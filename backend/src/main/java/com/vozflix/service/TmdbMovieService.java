package com.vozflix.service;

import com.google.gson.Gson;
import com.vozflix.api.TmdbApiService;
import com.vozflix.dao.GenreDao;
import com.vozflix.dao.MovieDao;
import com.vozflix.entity.Genre;
import com.vozflix.entity.Movie;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class TmdbMovieService {

    private final TmdbApiService tmdbApiService;
    private final MovieDao movieDao;
    private final GenreDao genreDao;
    private final Gson gson;

    @Value("${tmdb.api.image-base-url:https://image.tmdb.org/t/p}")
    private String imageBaseUrl;

    private static final String DEFAULT_LANGUAGE = "en-US";

    public Map<String, Object> getPopularMovies(Integer page) {
        try {
            return tmdbApiService.getPopularMovies(page, DEFAULT_LANGUAGE);
        } catch (Exception e) {
            log.error("Error fetching popular movies from TMDB", e);
            throw new RuntimeException("Failed to fetch popular movies", e);
        }
    }

    public Map<String, Object> getTopRatedMovies(Integer page) {
        try {
            return tmdbApiService.getTopRatedMovies(page, DEFAULT_LANGUAGE);
        } catch (Exception e) {
            log.error("Error fetching top rated movies from TMDB", e);
            throw new RuntimeException("Failed to fetch top rated movies", e);
        }
    }

    public Map<String, Object> getNowPlayingMovies(Integer page) {
        try {
            return tmdbApiService.getNowPlayingMovies(page, DEFAULT_LANGUAGE);
        } catch (Exception e) {
            log.error("Error fetching now playing movies from TMDB", e);
            throw new RuntimeException("Failed to fetch now playing movies", e);
        }
    }

    public Map<String, Object> getMovieDetails(Integer movieId) {
        try {
            return tmdbApiService.getMovieDetails(movieId, DEFAULT_LANGUAGE);
        } catch (Exception e) {
            log.error("Error fetching movie details for id: {}", movieId, e);
            throw new RuntimeException("Failed to fetch movie details", e);
        }
    }

    public Map<String, Object> getMovieCredits(Integer movieId) {
        try {
            return tmdbApiService.getMovieCredits(movieId, DEFAULT_LANGUAGE);
        } catch (Exception e) {
            log.error("Error fetching movie credits for id: {}", movieId, e);
            throw new RuntimeException("Failed to fetch movie credits", e);
        }
    }

    public Map<String, Object> getMovieImages(Integer movieId) {
        try {
            return tmdbApiService.getMovieImages(movieId);
        } catch (Exception e) {
            log.error("Error fetching movie images for id: {}", movieId, e);
            throw new RuntimeException("Failed to fetch movie images", e);
        }
    }

    public Map<String, Object> searchMovies(String query, Integer page) {
        try {
            return tmdbApiService.searchMovies(query, page, DEFAULT_LANGUAGE);
        } catch (Exception e) {
            log.error("Error searching movies: {}", query, e);
            throw new RuntimeException("Failed to search movies", e);
        }
    }

    @SuppressWarnings("unchecked")
    public void syncMovieGenres() {
        try {
            Map<String, Object> response = tmdbApiService.getMovieGenres(DEFAULT_LANGUAGE);
            List<Map<String, Object>> genres = (List<Map<String, Object>>) response.get("genres");

            if (genres != null) {
                genreDao.deleteAll();
                for (Map<String, Object> genreData : genres) {
                    Integer genreId = (Integer) genreData.get("id");
                    String name = (String) genreData.get("name");

                    Genre genre = Genre.builder()
                            .genreId(genreId)
                            .name(name)
                            .build();
                    genreDao.insert(genre);
                }
            }
        } catch (Exception e) {
            log.error("Error syncing movie genres", e);
            throw new RuntimeException("Failed to sync genres", e);
        }
    }

    public List<Movie> getCachedMovies(int limit, int offset) {
        return movieDao.findAll(limit, offset);
    }

    public List<Movie> getCachedPopularMovies(int limit, int offset) {
        return movieDao.findAll(limit, offset);
    }

    public Movie getCachedMovieById(Integer movieId) {
        return movieDao.findById(movieId).orElse(null);
    }
}