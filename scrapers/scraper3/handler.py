import json
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import boto3
from botocore.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure SQS connection to ElasticMQ (or AWS SQS)
sqs = boto3.client(
    'sqs',
    region_name='us-west-2',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    endpoint_url='http://sqs:9324',
    config=Config(retries={'max_attempts': 0}, connect_timeout=5, read_timeout=60)
)
SQS_QUEUE_URL = 'http://sqs:9324/000000000000/records_sqs'

def send_to_sqs(data):
    """Send scraped data to SQS queue."""
    try:
        logger.info("Sending data to SQS...")
        response = sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(data))
        logger.info(f"Message sent to SQS with ID: {response['MessageId']}")
    except Exception as e:
        logger.error(f"Failed to send message to SQS: {e}")

def clean_song_data(song):
    """Clean song data by replacing None with a placeholder."""
    logger.debug(f"Cleaning song data: {song}")
    for key, value in song.items():
        if value is None:
            song[key] = '-'
    return song

def scrape_billboard():
    """Scrape Billboard Hot 100 data and send raw data to SQS."""
    url = 'https://www.billboard.com/charts/hot-100/'
    logger.info(f"Scraping URL: {url}")
    
    try:
        res = requests.get(url, timeout=10)  # Added timeout to prevent hanging requests
        res.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to retrieve Billboard page: {e}")
        return {"message": "Failed to retrieve Billboard page."}

    soup = BeautifulSoup(res.text, 'html.parser')

    # Extract the formatted date
    date_elem = soup.find('p', class_='c-tagline a-font-primary-medium-xs u-font-size-11@mobile-max u-letter-spacing-0106 u-letter-spacing-0089@mobile-max lrv-u-line-height-copy lrv-u-text-transform-uppercase lrv-u-margin-a-00 lrv-u-padding-l-075 lrv-u-padding-l-00@mobile-max')
    if date_elem:
        date_str = date_elem.get_text(strip=True).replace('Week of ', '')
        try:
            date_obj = datetime.strptime(date_str, "%B %d, %Y")
            formatted_date = date_obj.strftime("%Y-%m-%d")  # Format date as YYYY-MM-DD
            logger.info(f"Scraped date: {formatted_date}")
        except ValueError as e:
            logger.error(f"Date parsing error: {e}")
            formatted_date = None
    else:
        formatted_date = None
        logger.warning("Could not find date on the page.")

    # Prepare the data structure for SQS message
    all_songs_data = []  # List to hold the formatted data

    data = {"us": []}  # Hardcoded to use "us" as an example (USA)

    chart_items = soup.find_all(attrs={'class': 'o-chart-results-list-row-container'}, limit=10)  # Limit to top 10 items
    if not chart_items:
        logger.warning("No chart items found on the page.")

    for e in chart_items:
        try:
            rank_elem = e.find('li', class_='o-chart-results-list__item')
            rank = rank_elem.find('span').get_text(strip=True) if rank_elem else None
            title_elem = e.h3
            title = title_elem.get_text(strip=True) if title_elem else None
            artist_elem = title_elem.find_next('span') if title_elem else None
            artist = artist_elem.get_text(strip=True) if artist_elem else None

            if not rank or not title or not artist:
                logger.warning("Incomplete song data found; skipping this entry.")
                continue
            
            # Extract last week, peak position, and weeks on chart
            last_week_elem = e.find('li', class_='o-chart-results-list__item // a-chart-color u-width-72 u-width-55@mobile-max u-width-55@tablet-only lrv-u-flex lrv-u-flex-shrink-0 lrv-u-align-items-center lrv-u-justify-content-center lrv-u-border-b-1 u-border-b-0@mobile-max lrv-u-border-color-grey-light u-background-color-white-064@mobile-max u-hidden@mobile-max')
            peak_pos_elem = last_week_elem.find_next_sibling('li') if last_week_elem else None
            wks_on_chart_elem = peak_pos_elem.find_next_sibling('li') if peak_pos_elem else None

            last_week = last_week_elem.find('span').get_text(strip=True) if last_week_elem else '-'
            peak_pos = peak_pos_elem.find('span').get_text(strip=True) if peak_pos_elem else '-'
            wks_on_chart = wks_on_chart_elem.find('span').get_text(strip=True) if wks_on_chart_elem else '-'

            # Prepare the song data to be processed later by the processor
            song_data = {
                'position': int(rank) if rank.isdigit() else None,
                'song': title,
                'artist': artist,
                'spotify_url': None,
                'album': 'Unknown',
                'duration': 'Unknown',
                'source': 'billboard_charts_hot_100',
                'songFeatures': {
                    'key': 'to be fetched in processor',
                    'genre': 'to be fetched in processor',
                    'language': 'to be fetched in processor'
                },
                'artistFeatures': {
                    'type': 'to be fetched in processor'
                }
            }

            # Log the scraped song data before cleaning
            logger.info(f"Scraped song data: {song_data}")

            cleaned_song_data = clean_song_data(song_data)
            data["us"].append(cleaned_song_data)
        except Exception as e:
            logger.error(f"Error processing element: {str(e)}")

    # Prepare the final message in the expected format
    sqs_message = [
        {
            "date": formatted_date,
            "charts": data
        }
    ]

    # Log the data before sending it to SQS
    logger.info(f"Data to be sent to SQS: {json.dumps(sqs_message, indent=2)}")

    # Send data to SQS
    send_to_sqs(sqs_message)

    return {"message": "Scraping completed and data sent to SQS."}

def lambda_handler(event, context):
    """AWS Lambda entry point."""
    logger.info("Scraper 3 is working")
    print("Scraper 3 is working")

    result = scrape_billboard()
    logger.info("Scraper 3 is finished")
    print("Scraper 3 is finished")
    logger.info(f"Scrape result: {result}")
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
