-- Create a table for storing chart dates
CREATE TABLE chart_dates (
    date DATE PRIMARY KEY
);

-- Create a table for storing countries
CREATE TABLE countries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

-- Create a table for storing artists
CREATE TABLE artists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    type VARCHAR(100) -- Type of artist, e.g., "Band", "Solo"
);

-- Create a table for storing songs
CREATE TABLE songs (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    artist_id INT NOT NULL,
    album VARCHAR(255),
    duration TIME,
    spotify_url VARCHAR(255),
    key VARCHAR(100),
    genre VARCHAR(100),
    language VARCHAR(100),
    FOREIGN KEY (artist_id) REFERENCES artists(id)
);

-- Create a table for storing sources
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

-- Create a table for managing song sources
CREATE TABLE song_sources (
    song_id INT NOT NULL,
    source_id INT NOT NULL,
    PRIMARY KEY (song_id, source_id),
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
);

-- Create a table for storing charts
CREATE TABLE charts (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    country_id INT NOT NULL,
    song_id INT NOT NULL,
    position INT NOT NULL,
    FOREIGN KEY (date) REFERENCES chart_dates(date) ON DELETE CASCADE,
    FOREIGN KEY (country_id) REFERENCES countries(id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
    UNIQUE (date, country_id, song_id) -- Ensures no duplicate entries for the same date, country, and song
);
