CREATE DATABASE movie_db;
USE movie_db;

CREATE TABLE IF NOT EXISTS movies (
    tmdb_id INT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    runtime INT, 
    vote_average DECIMAL(3, 1),
    overview TEXT, 
    release_date DATE,
    poster_path VARCHAR(255),
    raw_data JSON 
);

CREATE TABLE IF NOT EXISTS genres (
    id INT PRIMARY KEY,
    name VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS people (
    id INT PRIMARY KEY, 
    name VARCHAR(255) NOT NULL,
    profile_path VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id INT,
    genre_id INT,
    PRIMARY KEY (movie_id, genre_id),
    FOREIGN KEY (movie_id) REFERENCES movies(tmdb_id),
    FOREIGN KEY (genre_id) REFERENCES genres(id)
);

CREATE TABLE IF NOT EXISTS movie_cast (
    movie_id INT,
    person_id INT,
    character_name VARCHAR(255), 
    cast_order INT, 
    PRIMARY KEY (movie_id, person_id),
    FOREIGN KEY (movie_id) REFERENCES movies(tmdb_id),
    FOREIGN KEY (person_id) REFERENCES people(id)
);

CREATE TABLE IF NOT EXISTS movie_crew (
    movie_id INT,
    person_id INT,
    job VARCHAR(50), 
    PRIMARY KEY (movie_id, person_id, job),
    FOREIGN KEY (movie_id) REFERENCES movies(tmdb_id),
    FOREIGN KEY (person_id) REFERENCES people(id)
);

