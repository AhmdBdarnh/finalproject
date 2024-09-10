import os
import logging
import json
import time
import requests
import boto3
import spotipy
from botocore.config import Config
from spotipy.oauth2 import SpotifyClientCredentials
from crud.handler import (get_db_connection,
                          add_chart,
                          add_song,
                          add_artist,
                          add_song_source,
                          add_country,
                          add_chart_date,
                          ArtistData,
                          SongFeatures,
                          ArtistFeatures,
                          SongData,
                          ChartData, SongRequest)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Fetch environment variables
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'test')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')
SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL', 'http://sqs:9324/000000000000/records_sqs')
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID', 'bc6df3eb13b547769c8e7b761b1cf458')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET', 'bc9faad6721d4e998656b89ff853f4db')

logging.info(f"Using AWS_ACCESS_KEY_ID: {AWS_ACCESS_KEY_ID}")
logging.info(f"Using AWS_SECRET_ACCESS_KEY: {AWS_SECRET_ACCESS_KEY}")
logging.info(f"Using AWS_REGION: {AWS_REGION}")
logging.info(f"Using SQS_QUEUE_URL: {SQS_QUEUE_URL}")

# Configure the SQS client with ElasticMQ endpoint
sqs = boto3.client(
    'sqs',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    endpoint_url='http://sqs:9324',  # Local ElasticMQ endpoint
    config=Config(retries={'max_attempts': 0}, connect_timeout=5, read_timeout=60)
)

# Setup Spotify API client
sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET),
    requests_timeout=100  # Increase the timeout to 20 seconds
)


def fetch_artist_data(artist_name):
    """Fetch artist data from MusicBrainz API."""
    try:
        url = f"https://musicbrainz.org/ws/2/artist/?query=artist:{artist_name}&fmt=json"
        response = requests.get(url)
        if response.ok:
            data = response.json()
            artist_info = data['artists'][0] if data['artists'] else {}
            logging.info(f"Fetched artist data for artist: {artist_name}")
            return {
                'artist_name': artist_info.get('name', 'Unknown'),
                'country': artist_info.get('country', 'Unknown'),
                'gender': artist_info.get('gender', 'Unknown'),
                'disambiguation': artist_info.get('disambiguation', 'None'),
                'aliases': ', '.join(alias['name'] for alias in artist_info.get('aliases', [])),
                'tags': ', '.join(tag['name'] for tag in artist_info.get('tags', [])),
                'type': artist_info.get('type', 'Unknown')  # Fetch artist type
            }
    except Exception as e:
        logging.error(f"Error fetching artist data: {e}")
    return None


def fetch_song_features(song_name, artist_name, max_retries=5):
    """Fetch song features, genre, album, duration, and Spotify URL from Spotify API using song and artist names."""
    try:
        # Search for the song on Spotify using song and artist names
        query = f"track:{song_name} artist:{artist_name}"
        results = sp.search(q=query, type='track', limit=1)

        if not results['tracks']['items']:
            return {
                'key': 'Unknown',
                'genre': 'Unknown',
                'language': 'Unknown',
                'album': 'Unknown',
                'duration': 'Unknown',
                'spotify_url': None
            }

        # Extract track details from the search results
        track = results['tracks']['items'][0]
        track_id = track['id']  # Get the track ID
        spotify_url = track['external_urls']['spotify']  # Get the Spotify URL for the track
        album_name = track['album']['name'] if 'album' in track and track['album']['name'] else 'Unknown'  # Get the album name
        duration_ms = track['duration_ms']  # Get the track duration in milliseconds

        # Convert duration to minutes:seconds format
        if duration_ms is not None:
            duration_minutes = duration_ms // 60000
            duration_seconds = (duration_ms % 60000) // 1000
            duration = f"{duration_minutes}:{duration_seconds:02d}"  # Format as mm:ss
        else:
            duration = 'Unknown'

        logging.info(f"Found track '{track['name']}' by '{artist_name}' on Spotify with ID: {track_id}")

        # Fetch audio features for the track with retries
        retries = 0
        while retries < max_retries:
            try:
                # Fetch audio features for the track
                features = sp.audio_features(track_id)[0] if sp.audio_features(track_id) else {}

                # Fetch the artist information for genre
                artist_id = track['artists'][0]['id']  # Get the first artist ID from track
                artist = sp.artist(artist_id)  # Fetch artist details, including genre

                # Return key, genre, language, album, duration, and Spotify URL
                return {
                    'key': features.get('key', 'Unknown'),  # Key from audio features
                    'genre': ', '.join(artist.get('genres', ['Unknown'])),  # Genres from artist details
                    'language': 'Unknown',  # Spotify does not directly provide language; set it to 'Unknown'
                    'album': album_name,  # Album name
                    'duration': duration,  # Duration in mm:ss format
                    'spotify_url': spotify_url  # Spotify URL for the track
                }

            except spotipy.exceptions.SpotifyException as e:
                if e.http_status == 429:  # Too Many Requests
                    retry_after = int(e.headers.get("Retry-After", 1))  # Retry after time in seconds
                    logging.warning(f"Rate limit reached. Retrying after {retry_after} seconds.")
                    time.sleep(retry_after)
                    retries += 1
                else:
                    raise e  # Re-raise other exceptions
            except Exception as e:
                logging.error(f"Error fetching song features for '{song_name}' by '{artist_name}': {e}")
                break

        logging.error(f"Max retries reached for fetching song features for '{song_name}' by '{artist_name}'.")

    except Exception as e:
        logging.error(f"Error fetching song features for '{song_name}' by '{artist_name}': {e}")
    
    return {
        'key': 'Unknown',
        'genre': 'Unknown',
        'language': 'Unknown',
        'album': 'Unknown',
        'duration': 'Unknown',
        'spotify_url': None
    }



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_single_message(message):
    """Process an individual message."""
    try:
        # Parse the message body from JSON string to Python dictionary if it is a string
        if isinstance(message, str):
            message = json.loads(message)  # Deserialize JSON string to a Python dictionary

        logging.info(f"Processing single message: {json.dumps(message)}")
        
        date = message.get('date')
        charts = message.get('charts', {})

        # Loop through countries and their respective charts
        for country_name, country_charts in charts.items():
            # Insert country if not exists
            print(country_name)
            country_id = add_country(country_name)  # Ensure country is passed as a string

            # Ensure the date is added
            add_chart_date(date)

            for song in country_charts:
                position = song.get('position')
                song_title = song.get('song')
                artist_name = song.get('artist')
                album = song.get('album')
                duration = song.get('duration')

                # Fetch artist data
                artist_data = fetch_artist_data(artist_name)

                # Check if artist_data is None before accessing its attributes
                if artist_data is None:
                    # logging.warning(f"No artist data found for artist: {artist_name}")
                    artist_type = 'Unknown'
                else:
                    artist_type = artist_data.get('type', 'Unknown')

                # Create an ArtistData object
                artist = ArtistData(
                    name=artist_name,
                    type=artist_type
                )

                # Check if the artist already exists in the database
                artist_id = add_artist(artist)  # Modify add_artist to check if the artist exists

                # Fetch song features from Spotify API
                if song_title and artist_name:
                    logging.info(f"Fetching song features for '{song_title}' by '{artist_name}' from Spotify.")
                    song_features = fetch_song_features(song_title, artist_name)
                else:
                    song_features = {
                        'key': 'Unknown',
                        'genre': 'Unknown',
                        'language': 'Unknown',
                        'spotify_url': None
                    }

                # Ensure song features are strings or simple types
                key = song_features.get('key', 'Unknown')
                genre = song_features.get('genre', 'Unknown')
                language = song_features.get('language', 'Unknown')
                spotify_url = song_features.get('spotify_url')

                logging.info(f"Song '{song_title}' features: Key={key}, Genre={genre}, Language={language}, Spotify URL={spotify_url}")

                # Ensure duration is in a valid time format or set a default
                if duration == 'Unknown' or not duration:
                    duration = '00:00:00'  # Set default duration if it's not valid

                # Check if the song already exists in the database
                song_id = add_song(
                    title=song_title,
                    artist_id=artist_id,
                    album=album,
                    duration=duration,
                    spotify_url=spotify_url,  # Now passing the Spotify URL
                    key=key,
                    genre=genre,
                    language=language
                )

                # Check if the song source already exists
                source = song.get('source', 'Unknown')
                add_song_source(song_id, source)  # Modify add_song_source to check for existing sources

                # Check if the chart entry already exists
                add_chart(date, country_id, song_id, position)  # Modify add_chart to check for existing entries

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")


    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")



def lambda_handler(event, context):
    """AWS Lambda handler to process SQS messages."""
    logging.info(f"Received event: {json.dumps(event)}")

    for record in event.get('Records', []):
        # Correctly deserialize the JSON string into an object
        message_body = json.loads(record['body'])
        print("Processor  =======================================================")
        logging.info(f"Message received: {json.dumps(message_body)}")

        # If message_body is a list, process each message individually
        for message in message_body:
            process_single_message(message)

        print("Finished  =======================================================")

    return {
        'statusCode': 200,
        'body': json.dumps('Processing complete')
    }
