import psycopg2
from fastapi import FastAPI, HTTPException ,Query,Path
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import datetime
import logging
import time
from fastapi.middleware.cors import CORSMiddleware
import psycopg2.extras

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Allow specific origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Models
class SongFeatures(BaseModel):
    key: Optional[str]
    genre: Optional[str]
    language: Optional[str]

class ArtistFeatures(BaseModel):
    type: Optional[str]

class SongData(BaseModel):
    position: int
    song: str
    artist: str
    album: Optional[str]
    duration: Optional[str]
    spotify_url: Optional[str]
    songFeatures: SongFeatures
    artistFeatures: ArtistFeatures

class ChartData(BaseModel):
    date: str
    country: str
    charts: Dict[str, List[SongData]]

class ArtistData(BaseModel):
    name: str
    type: Optional[str]

class SongRequest(BaseModel):
    position: int
    title: str
    artist_id: int
    album: Optional[str]
    duration: Optional[str]
    spotify_url: Optional[str]
    key: Optional[str]
    genre: Optional[str]
    language: Optional[str]


class SongCreateRequest(BaseModel):
    title: str
    artist_id: int
    album: str = None
    duration: str = None
    spotify_url: str = None
    key: str = None
    genre: str = None
    language: str = None


class SongUpdateRequest(BaseModel):
    title: str
    artist_id: int
    album: str = None
    duration: str = None
    spotify_url: str = None
    key: str = None
    genre: str = None
    language: str = None


def get_db_connection(retries=5, delay=5):  # Increased retries and delay
    for i in range(retries):
        try:
            connection = psycopg2.connect(
                dbname="music_db",
                user="user",
                password="password",
                host="db",  # Make sure this matches the service name in docker-compose
                port="5432"
            )
            logging.info("Database connection established")
            return connection
        except Exception as e:
            logging.error(f"Database connection failed, retrying in {delay} seconds... ({i+1}/{retries})")
            time.sleep(delay)
    raise Exception("Database connection failed after multiple attempts")




# Function to get all songs
@app.get("/songs", response_model=List[Dict])
def get_all_songs():
    connection = get_db_connection()
    try:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, title, album, duration, spotify_url, key, genre, language, artist_id 
                FROM songs;
            """)
            songs = cursor.fetchall()
            if not songs:
                raise HTTPException(status_code=404, detail="No songs found")
            return songs
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e.pgcode} - {e.pgerror}")
    finally:
        connection.close()




# Function to get a song by its ID
@app.get("/songs/{song_id}", response_model=Dict)
def get_song_by_id(song_id: int = Path(..., description="The ID of the song to retrieve")):
    connection = get_db_connection()
    try:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, title, album, duration, spotify_url, key, genre, language, artist_id
                FROM songs
                WHERE id = %s;
            """, (song_id,))
            song = cursor.fetchone()

        if not song:
            raise HTTPException(status_code=404, detail=f"Song with id {song_id} not found")

        return song

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e.pgcode} - {e.pgerror}")

    finally:
        connection.close()






# Function to update a song by ID
@app.put("/songs/{song_id}", response_model=Dict)
def update_song(song_id: int, song: SongUpdateRequest):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE songs 
            SET title = %s, artist_id = %s, album = %s, duration = %s, spotify_url = %s, 
                key = %s, genre = %s, language = %s 
            WHERE id = %s
            RETURNING *;
        """, (song.title, song.artist_id, song.album, song.duration, song.spotify_url,
              song.key, song.genre, song.language, song_id))

        updated_song = cursor.fetchone()
        connection.commit()
        if not updated_song:
            raise HTTPException(status_code=404, detail=f"Song with id {song_id} not found")

        return {
            "id": updated_song[0],
            "title": updated_song[1],
            "artist_id": updated_song[2],
            "album": updated_song[3],
            "duration": updated_song[4],
            "spotify_url": updated_song[5],
            "key": updated_song[6],
            "genre": updated_song[7],
            "language": updated_song[8]
        }

    except psycopg2.Error as e:
        connection.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {e.pgcode} - {e.pgerror}")
    
    finally:
        cursor.close()
        connection.close()


@app.post("/songs", response_model=int)
def create_song(song: SongCreateRequest):
    """
    Create a new song in the database.
    """
    try:
        # Use the function you've defined to add the song
        song_id = add_song(
            title=song.title,
            artist_id=song.artist_id,
            album=song.album,
            duration=song.duration,
            spotify_url=song.spotify_url,
            key=song.key,
            genre=song.genre,
            language=song.language
        )
        return song_id
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal error occurred")

# Ensure logging is configured to capture essential info
logging.basicConfig(level=logging.INFO)




# Function to add a new song
def add_song(title, artist_id, album=None, duration=None, spotify_url=None, key=None, genre=None, language=None):
    """
    Insert a song into the songs table without checking for conflicts.
    """
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO songs (title, artist_id, album, duration, spotify_url, key, genre, language)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (title, artist_id, album, duration, spotify_url, key, genre, language)
        )
        song_id = cursor.fetchone()[0]
        connection.commit()
        logging.info(f"Song added: {title} by artist_id {artist_id}, song_id {song_id}")
        return song_id

    except Exception as e:
        connection.rollback()
        logging.error(f"Failed to insert song {title}: {e}")
        raise HTTPException(status_code=500, detail="Failed to insert song")

    finally:
        cursor.close()
        connection.close()


# Function to add a country
def add_country(country_name):
    """Insert or fetch the country ID based on the country name."""
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = connection.cursor()

    try:
        # Ensure the country name is a string and query the database
        cursor.execute("SELECT id FROM countries WHERE name = %s", (country_name,))
        country = cursor.fetchone()

        # If the country doesn't exist, insert it
        if not country:
            cursor.execute("INSERT INTO countries (name) VALUES (%s) RETURNING id", (country_name,))
            country_id = cursor.fetchone()[0]
            connection.commit()
            logging.info(f"Inserted new country: {country_name} with id {country_id}")
        else:
            country_id = country[0]
            logging.info(f"Country '{country_name}' already exists with id {country_id}")

        return country_id

    except Exception as e:
        connection.rollback()
        logging.error(f"Failed to insert or fetch country '{country_name}': {e}")
        raise HTTPException(status_code=500, detail="Failed to insert or fetch country")

    finally:
        cursor.close()
        connection.close()




# Function to add a chart date
def add_chart_date(date):
    """
    Insert a date into the chart_dates table if it does not exist.
    """
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Insert date if it does not exist using ON CONFLICT DO NOTHING
        cursor.execute(
            "INSERT INTO chart_dates (date) VALUES (%s) ON CONFLICT (date) DO NOTHING;",
            (date,)
        )
        connection.commit()
        logging.info(f"Chart date '{date}' added to chart_dates table")

    except Exception as e:
        connection.rollback()
        logging.error(f"Failed to insert or retrieve chart date '{date}': {e}")
        raise HTTPException(status_code=500, detail="Failed to insert or retrieve chart date")

    finally:
        cursor.close()
        connection.close()



# Function to add a song source
def add_song_source(song_id, source_name):
    """
    Add a source for a song in the song_sources table. If the source does not exist, it will be inserted.
    """
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT id FROM sources WHERE name = %s", (source_name,))
        source_id = cursor.fetchone()

        if not source_id:
            cursor.execute("INSERT INTO sources (name) VALUES (%s) RETURNING id", (source_name,))
            source_id = cursor.fetchone()[0]
            connection.commit()
            logging.info(f"Source '{source_name}' added with id {source_id}")
        else:
            source_id = source_id[0]

        cursor.execute(
            """
            INSERT INTO song_sources (song_id, source_id)
            VALUES (%s, %s)
            ON CONFLICT (song_id, source_id) DO NOTHING;
            """,
            (song_id, source_id)
        )
        connection.commit()
        logging.info(f"Song source relationship added for song_id {song_id} and source_id {source_id}")

    except Exception as e:
        connection.rollback()
        logging.error(f"Failed to insert song source for song_id {song_id} and source '{source_name}': {e}")
        raise HTTPException(status_code=500, detail="Failed to insert song source")

    finally:
        cursor.close()
        connection.close()


# Function to add chart entry
def add_chart(date, country_id, song_id, position):
    """
    Insert a chart entry into the charts table. If it already exists, do nothing.
    """
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Insert the chart data; if it exists, it will not insert again due to UNIQUE constraint.
        cursor.execute("""
            INSERT INTO charts (date, country_id, song_id, position)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (date, country_id, song_id) DO UPDATE SET position = EXCLUDED.position;
        """, (date, country_id, song_id, position))

        connection.commit()
        logging.info(f"Chart data inserted or updated for date {date}, country {country_id}, song {song_id}, position {position}")

    except Exception as e:
        connection.rollback()
        logging.error(f"Failed to insert or update chart data: {e}")
        raise HTTPException(status_code=500, detail="Failed to insert or update chart data")

    finally:
        cursor.close()
        connection.close()




@app.get("/charts", response_model=Dict)
def get_charts(date: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$")):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Validate the date format
        datetime.datetime.strptime(date, '%Y-%m-%d')

        # Query to get charts data for a specific date from 'youtube_RightNow' source
        cursor.execute("""
            SELECT c.name, ch.position, s.title, a.name, s.album, s.duration, s.spotify_url, s.key, s.genre, s.language, a.type
            FROM charts ch
            JOIN countries c ON ch.country_id = c.id
            JOIN songs s ON ch.song_id = s.id
            JOIN artists a ON s.artist_id = a.id
            JOIN song_sources ss ON s.id = ss.song_id
            JOIN sources src ON ss.source_id = src.id
            WHERE ch.date = %s AND src.name = 'youtube_RightNow'
            ORDER BY c.name, ch.position;
        """, (date,))

        rows = cursor.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="No chart data found for the given date")

        # Structure data into the required response format
        charts = {}
        for row in rows:
            country = row[0]
            song_data = {
                "position": row[1],
                "song": row[2],
                "artist": row[3],
                "album": row[4],
                "duration": str(row[5]),
                "spotify_url": row[6],
                "songFeatures": {
                    "key": row[7],
                    "genre": row[8],
                    "language": row[9]
                },
                "artistFeatures": {
                    "type": row[10]
                }
            }

            if country not in charts:
                charts[country] = []

            charts[country].append(song_data)

        return {"date": date, "charts": charts}

    except Exception as e:
        logging.error(f"Failed to fetch chart data for date '{date}': {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chart data")

    finally:
        cursor.close()
        connection.close()


@app.get("/charts/available-dates", response_model=Dict)
def get_available_dates():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Query to get all available dates
        cursor.execute("SELECT date FROM chart_dates ORDER BY date;")
        rows = cursor.fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail="No available dates found")

        # Structure data into the required response format
        available_dates = {}
        for row in rows:
            date = row[0]
            year = date.year
            month = date.month
            day = date.day

            if str(year) not in available_dates:
                available_dates[str(year)] = {}

            if str(month) not in available_dates[str(year)]:
                available_dates[str(year)][str(month)] = []

            available_dates[str(year)][str(month)].append(str(day))

        return available_dates

    except Exception as e:
        logging.error(f"Failed to fetch available dates: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch available dates")

    finally:
        cursor.close()
        connection.close()




# Function to add a new artist
@app.post("/artists")
def add_artist(artist: ArtistData):
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = connection.cursor()

    try:
        # Check if the artist already exists
        cursor.execute("SELECT id FROM artists WHERE name = %s", (artist.name,))
        artist_id = cursor.fetchone()

        if artist_id:
            logging.info(f"Artist '{artist.name}' already exists, returning existing ID")
            return artist_id[0]  # Return the existing artist's ID

        # Insert the artist into the artists table
        cursor.execute("""
            INSERT INTO artists (name, type)
            VALUES (%s, %s)
            RETURNING id;
        """, (artist.name, artist.type))
        
        artist_id = cursor.fetchone()[0]
        connection.commit()
        logging.info(f"Artist '{artist.name}' inserted with id {artist_id}")

        return artist_id

    except Exception as e:
        connection.rollback()
        logging.error(f"Failed to insert artist '{artist.name}': {e}")
        raise HTTPException(status_code=500, detail="Failed to insert artist")

    finally:
        cursor.close()
        connection.close()



@app.get("/artists", response_model=List[ArtistData])
def get_all_artists():
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id, name, type FROM artists;")
        artists = cursor.fetchall()
        if not artists:
            raise HTTPException(status_code=404, detail="No artists found")
        return [{"id": artist[0], "name": artist[1], "type": artist[2]} for artist in artists]
    except Exception as e:
        logging.error(f"Error fetching artists: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch artists")
    finally:
        cursor.close()
        connection.close()




@app.get("/artists/{artist_id}", response_model=ArtistData)
def get_artist_by_id(artist_id: int):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT id, name, type FROM artists WHERE id = %s", (artist_id,))
        artist = cursor.fetchone()
        if not artist:
            raise HTTPException(status_code=404, detail="Artist not found")
        return {"id": artist[0], "name": artist[1], "type": artist[2]}
    except Exception as e:
        logging.error(f"Error fetching artist by ID {artist_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch artist with ID {artist_id}")
    finally:
        cursor.close()
        connection.close()



@app.put("/artists/{artist_id}", response_model=ArtistData)
def update_artist(artist_id: int, artist: ArtistData):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE artists
            SET name = %s, type = %s
            WHERE id = %s
            RETURNING id, name, type;
        """, (artist.name, artist.type, artist_id))
        updated_artist = cursor.fetchone()
        connection.commit()
        if not updated_artist:
            raise HTTPException(status_code=404, detail="Artist not found")
        return {"id": updated_artist[0], "name": updated_artist[1], "type": updated_artist[2]}
    except Exception as e:
        connection.rollback()
        logging.error(f"Failed to update artist {artist_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update artist with ID {artist_id}")
    finally:
        cursor.close()
        connection.close()





