Here's the updated README file including the new API documentation:

---

# Music Scrapers Project

## Overview
This project implements three scrapers that fetch data from YouTube and Billboard charts. The scrapers collect the top 10 song titles from various countries' formal charts and push the data into an SQS queue. The scrapers include:

1. **YouTube Hot 100 Scraper**
2. **YouTube Trending 30 Scraper**
3. **Billboard Hot 100 Scraper**

Each scraper targets a specific chart and collects the top 10 songs by country, which are then pushed to the corresponding SQS queue for further processing.

A Lambda function is triggered by SQS events to fetch the song data and enrich it with more information using Spotify APIs. The processor fetches song features, artist information, and additional metadata and stores the data in a PostgreSQL database using CRUD API endpoints.

## Features
- Scrapes top 10 songs for each country in YouTube and Billboard charts.
- Enriches scraped data with Spotify API to retrieve additional song and artist details.
- Stores data in a PostgreSQL database using a CRUD API.
- APIs for adding and editing songs and artists.
- Scheduled scrapers run every 5 minutes.

## Requirements
To run this project, ensure you have the following installed:
- Docker
- Docker Compose
- PostgreSQL (configured inside Docker Compose)
- AWS credentials (for local SQS)

## Setup and Running the Project
1. **Clone the Repository**
   ```bash
   git clone <repository_url>
   cd music-scrapers
   ```

2. **Build and Run with Docker Compose**
   ```bash
   docker compose build
   docker compose up
   ```

3. **Activate the UI Browser for Pulse Data**
   After Docker containers are up and running, navigate to the UI browser interface to manage and monitor the data:
   ```bash
   cd pulse-data
   ```

4. **Test the APIs with Postman**
   You can test the CRUD APIs using Postman. Appropriate HTTP methods should be created according to the API structure. To access the API documentation and test endpoints, use the following link:
   [API Documentation](https://documenter.getpostman.com/view/32173427/2sAXjSyTqW)

## API Endpoints to Activate Scrapers and Processor
In addition to the scheduled scrapers running every 5 minutes, you can manually trigger them using the following API endpoints to skip the waiting time:

- **Scraper 1 (YouTube Hot 100)**  
  - GET: `http://localhost:3000/dev/scrape1` => To Run the scrpaer1- youtube trend100
  - POST: `http://localhost:3000/2015-03-31/functions/scraper1/invocations`
  
- **Scraper 2 (YouTube Trending 30)**  
  - GET: `http://localhost:3000/dev/scrape`  => "To Run the scraper2 script to fetch the top 30 trending videos on YouTube. This scraper is connected to the UI, allowing the data to be displayed directly on the interface."
  - POST: `http://localhost:3000/2015-03-31/functions/scraper2/invocations`
  
- **Scraper 3 (Billboard Hot 100)**  
  - GET: `http://localhost:3000/dev/scrape3` => To Run the scrpaer3- billborads
  - POST: `http://localhost:3000/2015-03-31/functions/scraper3/invocations`

- **Processor (Triggered by SQS Events)**  
  - GET: `http://localhost:3000/dev/process`  
  - POST: `http://localhost:3000/2015-03-31/functions/processor/invocations`

These endpoints can be used to activate the scrapers and processor immediately, bypassing the scheduled execution configured in the `serverless.yml` file.

## Available CRUD APIs
- **Add Song**
- **Edit Song**
- **Add Artist**
- **Edit Artist**
- **Get Available Dates**
- **Get Charts**

Use the API documentation for detailed information on endpoints and usage.

## Scraper Schedule
The scrapers are scheduled to run periodically to ensure that the data remains fresh and up-to-date. Each scraper fetches the latest top trending songs or videos and updates the data every few minutes.

- **Scraper 1**: Runs every 5 minutes. It starts its first run after 5 minutes and continues to run at 5-minute intervals.
- **Scraper 2**: Runs every 10 minutes. It begins its first run after 10 minutes and continues to run at 10-minute intervals.
- **Scraper 3**: Runs every 15 minutes. It starts its first run after 15 minutes and continues to run at 15-minute intervals.

These intervals ensure that the top trending songs or videos are updated frequently, providing fresh and current data.

## Contributions
Feel free to contribute to the project by submitting pull requests, suggesting improvements, or reporting issues.

## How to Run the Project

To run the project and access the scraping services via Docker, follow these steps:

1. **Start the Project with Docker Compose**:
   
   Navigate to the project directory and use the following command to build and start all the necessary services:

   ```bash
   docker-compose up --build
   ```
2. Wait for the Services to Initialize:

pipeline-1  |  ┌───────────────────────────────────────────────────────────────────────────┐
pipeline-1  |  │                                                                           │
pipeline-1  |  │   GET  | http://0.0.0.0:3000/dev/scrape                                   │
pipeline-1  |  │   POST | http://0.0.0.0:3000/2015-03-31/functions/scraper2/invocations    │
pipeline-1  |  │   GET  | http://0.0.0.0:3000/dev/scrape1                                  │
pipeline-1  |  │   POST | http://0.0.0.0:3000/2015-03-31/functions/scraper1/invocations    │
pipeline-1  |  │   GET  | http://0.0.0.0:3000/dev/scrape3                                  │
pipeline-1  |  │   POST | http://0.0.0.0:3000/2015-03-31/functions/scraper3/invocations    │
pipeline-1  |  │   GET  | http://0.0.0.0:3000/dev/process                                  │
pipeline-1  |  │   POST | http://0.0.0.0:3000/2015-03-31/functions/processor/invocations   │
pipeline-1  |  │                                                                           │
pipeline-1  |  └───────────────────────────────────────────────────────────────────────────┘

3. Access the Scraping Endpoint:

http://localhost:3000/dev/scrape

4. Run the UI

cd .\pulse-app\
npm i
npm run start