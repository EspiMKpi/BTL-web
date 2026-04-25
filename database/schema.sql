-- VozFlix Database Schema
-- Movie streaming platform database with TMDB API data integration

-- ============================================================
-- CREATE DATABASE
-- ============================================================

CREATE DATABASE IF NOT EXISTS movie_db;
USE movie_db;

-- ============================================================
-- USERS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    role ENUM('user', 'admin', 'curator') DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_email (email),
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- GENRES TABLE (TMDB Genre Reference)
-- ============================================================

CREATE TABLE IF NOT EXISTS genres (
    genre_id INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_genre_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- MOVIES TABLE (Cached TMDB Data)
-- ============================================================

CREATE TABLE IF NOT EXISTS movies (
    movie_id INT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    original_title VARCHAR(255),
    tagline VARCHAR(500),
    overview TEXT,
    poster_path VARCHAR(500),
    backdrop_path VARCHAR(500),
    release_date DATE,
    original_language VARCHAR(10),
    popularity DECIMAL(10, 4),
    vote_average DECIMAL(3, 1),
    vote_count INT,
    adult BOOLEAN DEFAULT FALSE,
    video BOOLEAN DEFAULT FALSE,
    runtime INT,
    budget BIGINT,
    revenue BIGINT,
    status VARCHAR(20),
    imdb_id VARCHAR(20),
    homepage VARCHAR(500),
    genres_json JSON,
    production_countries_json JSON,
    spoken_languages_json JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_title (title),
    INDEX idx_release_date (release_date),
    INDEX idx_vote_average (vote_average),
    INDEX idx_popularity (popularity),
    FULLTEXT INDEX ft_title (title, original_title, overview)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- SERIES TABLE (TMDB TV Shows)
-- ============================================================

CREATE TABLE IF NOT EXISTS series (
    series_id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    original_name VARCHAR(255),
    tagline VARCHAR(500),
    overview TEXT,
    poster_path VARCHAR(500),
    backdrop_path VARCHAR(500),
    first_air_date DATE,
    last_air_date DATE,
    original_language VARCHAR(10),
    popularity DECIMAL(10, 4),
    vote_average DECIMAL(3, 1),
    vote_count INT,
    adult BOOLEAN DEFAULT FALSE,
    episode_run_time_json JSON,
    type VARCHAR(30),
    status VARCHAR(20),
    imdb_id VARCHAR(20),
    homepage VARCHAR(500),
    genres_json JSON,
    networks_json JSON,
    production_countries_json JSON,
    spoken_languages_json JSON,
    number_of_seasons INT,
    number_of_episodes INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_first_air_date (first_air_date),
    INDEX idx_vote_average (vote_average),
    INDEX idx_popularity (popularity),
    FULLTEXT INDEX ft_name (name, original_name, overview)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- SEASONS TABLE (TMDB TV Seasons)
-- ============================================================

CREATE TABLE IF NOT EXISTS seasons (
    season_id INT PRIMARY KEY,
    season_number INT NOT NULL,
    series_id INT NOT NULL,
    name VARCHAR(255),
    overview TEXT,
    poster_path VARCHAR(500),
    air_date DATE,
    episode_count INT,
    vote_average DECIMAL(3, 1),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (series_id) REFERENCES series(series_id) ON DELETE CASCADE,
    UNIQUE KEY uk_series_season (series_id, season_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- EPISODES TABLE (TMDB TV Episodes)
-- ============================================================

CREATE TABLE IF NOT EXISTS episodes (
    episode_id INT PRIMARY KEY,
    episode_number INT NOT NULL,
    season_number INT NOT NULL,
    series_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    overview TEXT,
    still_path VARCHAR(500),
    air_date DATE,
    runtime INT,
    vote_average DECIMAL(3, 1),
    vote_count INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (series_id) REFERENCES series(series_id) ON DELETE CASCADE,
    UNIQUE KEY uk_series_season_ep (series_id, season_number, episode_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- CASTS TABLE (Actors/Crew for Movies)
-- ============================================================

CREATE TABLE IF NOT EXISTS casts (
    cast_id INT PRIMARY KEY,
    movie_id INT NOT NULL,
    credit_id VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    original_name VARCHAR(255),
    character_name VARCHAR(255),
    department VARCHAR(100),
    job VARCHAR(100),
    gender INT,
    profile_path VARCHAR(500),
    popularity DECIMAL(10, 4),
    ordering INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id) ON DELETE CASCADE,
    INDEX idx_cast_name (name),
    INDEX idx_movie_id (movie_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- SERIES_CASTS TABLE (Actors/Crew for TV Series)
-- ============================================================

CREATE TABLE IF NOT EXISTS series_casts (
    cast_id INT PRIMARY KEY,
    series_id INT NOT NULL,
    season_number INT,
    episode_id INT,
    credit_id VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    original_name VARCHAR(255),
    character_name VARCHAR(255),
    department VARCHAR(100),
    job VARCHAR(100),
    gender INT,
    profile_path VARCHAR(500),
    popularity DECIMAL(10, 4),
    ordering INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (series_id) REFERENCES series(series_id) ON DELETE CASCADE,
    INDEX idx_cast_name (name),
    INDEX idx_series_id (series_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- WATCHLIST ITEMS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS watchlist_items (
    watchlist_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    content_type ENUM('movie', 'series') NOT NULL,
    tmdb_id INT NOT NULL,
    status ENUM('continue', 'wishlist', 'completed', 'favorites') NOT NULL,
    progress_seconds INT DEFAULT 0,
    current_episode INT DEFAULT 1,
    current_season INT DEFAULT 1,
    rating DECIMAL(2, 1),
    review TEXT,
    is_bookmarked BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_content (user_id, content_type, tmdb_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_user_status (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- WATCH HISTORY TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS watch_history (
    history_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    content_type ENUM('movie', 'series') NOT NULL,
    tmdb_id INT NOT NULL,
    season_number INT,
    episode_number INT,
    progress_seconds INT DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    last_watched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_last_watched (last_watched_at),
    INDEX idx_user_content (user_id, content_type, tmdb_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- USER RATINGS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS user_ratings (
    rating_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    content_type ENUM('movie', 'series') NOT NULL,
    tmdb_id INT NOT NULL,
    rating DECIMAL(2, 1) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_content_rating (user_id, content_type, tmdb_id),
    INDEX idx_user_id (user_id),
    INDEX idx_tmdb_id (tmdb_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;