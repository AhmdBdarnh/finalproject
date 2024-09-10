import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import logging
import time
from datetime import datetime, timedelta  # Import timedelta for date calculations
import boto3
from botocore.config import Config

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
    try:
        # Send data as a list containing one dictionary, matching the format expected by the processor
        response = sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps([data]))
        logging.info(f"Message sent to SQS with ID: {response['MessageId']}")
        print("response ======================================================\n")
        print(response)
    except Exception as e:
        logging.error(f"Failed to send message to SQS: {e}")

# Map two-letter country codes to three-letter country codes
country_code_map = {
    "ar": "ARG",  # Argentina
    "au": "AUS",  # Australia
    "at": "AUT",  # Austria
}

def scrape_youtube_trending():
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # List of YouTube country codes
    country_codes = ["ar", "au", "at"]

    # Use yesterday's date
    yesterday_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    date_entry = {"date": yesterday_date, "charts": {}}
    
    for country_code in country_codes:
        url = f"https://charts.youtube.com/charts/TopVideos/{country_code}/daily?date={yesterday_date}"
        logging.info(f"Scraping URL: {url}")
        try:
            driver.get(url)
            time.sleep(10)
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, "html.parser")

            songs_data = []
            entries = soup.find_all('ytmc-entry-row')
            if not entries:
                logging.warning(f"No entries found on the page for {country_code} on {yesterday_date}.")
            else:
                logging.info(f"Found {len(entries)} entries. Limiting to top 10.")

            for i, entry in enumerate(entries[:10]):
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

                    # No Spotify fetching here, just pass the URL if available
                    spotify_url = None  # Placeholder for Spotify URL; processor will handle fetching
                    album_name = 'Unknown'  # Placeholder for album name
                    duration = 'Unknown'  # Placeholder for duration

                    # Add the placeholders to the song dictionary
                    song['spotify_url'] = spotify_url
                    song['album'] = album_name
                    song['duration'] = duration
                    song['source'] = 'youtube_charts_TopVideos'

                    # Add placeholders for song features and artist features; processor will fetch these
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

            three_letter_country_code = country_code_map.get(country_code, country_code.upper())
            date_entry["charts"][three_letter_country_code] = songs_data

        except Exception as e:
            logging.error(f"Failed to scrape URL {url}: {e}")

    # Send the entire date entry to SQS
    send_to_sqs(date_entry)

    driver.quit()

def lambda_handler(event, context):
    """AWS Lambda handler function"""
    logging.info("Starting the Lambda function to scrape YouTube trending data.")
    scrape_youtube_trending()
    logging.info("Scraping completed successfully.")
    return {
        'statusCode': 200,
        'body': json.dumps('Scraping completed successfully.')
    }
