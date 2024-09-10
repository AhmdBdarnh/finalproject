import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import logging
import time
from datetime import datetime
import boto3
from botocore.config import Config
import pytz  # Add this import for timezone handling

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure SQS connection to ElasticMQ
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
        response = sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(data))
        logging.info(f"Message sent to SQS with ID: {response['MessageId']}")
    except Exception as e:
        logging.error(f"Failed to send message to SQS: {e}")

# Map two-letter country codes to three-letter country codes
country_code_map = {
    "ar": "ARG",  # Argentina
    "au": "AUS",  # Australia
    "at": "AUT",  # Austria
    "be": "BEL",  # Belgium
    "bo": "BOL",  # Bolivia
    "br": "BRA",  # Brazil
    "ca": "CAN",  # Canada
    "cl": "CHL",  # Chile
    "co": "COL",  # Colombia
    "cr": "CRI",  # Costa Rica
    "cz": "CZE",  # Czechia
    "dk": "DNK",  # Denmark
    "do": "DOM",  # Dominican Republic
    "ec": "ECU",  # Ecuador
    "eg": "EGY",  # Egypt
    "sv": "SLV",  # El Salvador
    "ee": "EST",  # Estonia
}

def scrape_youtube_trending():
    """Scrape YouTube trending songs and send the data to SQS."""
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    # Automatically download and set up ChromeDriver
    service = Service(ChromeDriverManager().install())

    # Set up WebDriver
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # List of YouTube country codes
    country_codes = [
    "ar", "au", "at", "be", "bo", "br", "ca", "cl", "co", "cr", "cz", "dk", "do", "ec", "eg", "sv", "ee"
    ]  

    # Use today's date
    local_timezone = pytz.timezone("Asia/Jerusalem")  # Updated to Israel's timezone
    local_datetime = datetime.now(local_timezone)
    today_date = local_datetime.strftime('%Y-%m-%d')
    logging.info(f"Today's date for scraping: {today_date}")
    print(today_date)

    # List to accumulate all song data
    all_songs_data = []

    date_entry = {"date": today_date, "charts": {}}  # Entry for today

    for country_code in country_codes:
        url = f"https://charts.youtube.com/charts/TrendingVideos/{country_code}/RightNow"
        logging.info(f"Scraping URL: {url}")
        try:
            driver.get(url)
            time.sleep(10)  # Allow time for page to load

            # Parse the HTML content
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract only the top 10 songs
            songs_data = []
            entries = soup.find_all('ytmc-entry-row')
 
            for i, entry in enumerate(entries[:10]):  # Limit to top 10 songs
                try:
                    song = {}
                    rank_tag = entry.find('span', id='rank')
                    if rank_tag:
                        song['position'] = int(rank_tag.text.strip())

                    title_tag = entry.find('div', class_='title')
                    if title_tag:
                        song['song'] = title_tag.text.strip()

                    artist_tags = entry.find_all('span', class_='artistName')
                    song['artist'] = ', '.join([artist.text.strip() for artist in artist_tags])

                    # Spotify-related data fetching removed as per the processor's role
                    song['spotify_url'] = None  # Placeholder
                    song['album'] = 'Unknown'  # Placeholder
                    song['duration'] = 'Unknown'  # Placeholder
                    song['source'] = 'youtube_RightNow'

                    # Set songFeatures and artistFeatures as placeholders
                    song['songFeatures'] = {
                        'key': 'to be fetched in processor',
                        'genre': 'to be fetched in processor',
                        'language': 'to be fetched in processor'
                    }
                    song['artistFeatures'] = {
                        'type': 'to be fetched in processor'
                    }

                    songs_data.append(song)
                except Exception as e:
                    logging.error(f"Error extracting song data: {e}")

            # Convert two-letter country code to three-letter country code using the map
            three_letter_country_code = country_code_map.get(country_code, country_code.upper())

            # Accumulate data for this country under the specific date
            date_entry["charts"][three_letter_country_code] = songs_data

        except Exception as e:
            logging.error(f"Failed to scrape URL {url}: {e}")

    # Add date entry to the list
    all_songs_data.append(date_entry)

    # Send the scraped data to SQS
    send_to_sqs(all_songs_data)

    # Quit the WebDriver instance
    driver.quit()

def lambda_handler(event, context):
    """AWS Lambda handler function."""
    scrape_youtube_trending()
    return {
        'statusCode': 200,
        'body': json.dumps('Scraping and SQS operation completed.')
    }
