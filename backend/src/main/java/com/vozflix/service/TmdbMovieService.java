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
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import retrofit2.Call;
import retrofit2.Response;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class TmdbMovieService {

    private final TmdbApiService tmdbApiService;
    private final MovieDao movieDao;
    private final GenreDao genreDao;
    private final Gson gson;
    private final RedisTemplate<String, Object> redisTemplate;

    @Value("${search.cache.ttl:3600}")
    private long cacheTtlSeconds;

    @Value("${tmdb.api.image-base-url:https://image.tmdb.org/t/p}")
    private String imageBaseUrl;

    private static final String DEFAULT_LANGUAGE = "en-US";

    private Map<String, Object> executeCall(Call<Map<String, Object>> call) {
        try {
            Response<Map<String, Object>> response = call.execute();
            if (response.isSuccessful() && response.body() != null) {
                return response.body();
            }
            throw new RuntimeException("TMDB request failed with status " + response.code());
        } catch (Exception e) {
            throw new RuntimeException("TMDB request failed", e);
        }
    }

    public Map<String, Object> getPopularMovies(Integer page) {
        String cacheKey = "movies:popular:" + page;
        try { Object cached = redisTemplate.opsForValue().get(cacheKey); if (cached != null) return convertToMap(cached); } catch (Exception e) {}
        try {
            Map<String, Object> response = executeCall(tmdbApiService.getPopularMovies(page, DEFAULT_LANGUAGE));
            cacheMovieListResponse(response);
            try { redisTemplate.opsForValue().set(cacheKey, response, cacheTtlSeconds, TimeUnit.SECONDS); } catch (Exception e) {}
            return response;
        } catch (Exception e) {
            log.error("Error fetching popular movies from TMDB", e);
            throw new RuntimeException("Failed to fetch popular movies", e);
        }
    }

    public Map<String, Object> getTopRatedMovies(Integer page) {
        String cacheKey = "movies:top_rated:" + page;
        try { Object cached = redisTemplate.opsForValue().get(cacheKey); if (cached != null) return convertToMap(cached); } catch (Exception e) {}
        try {
            Map<String, Object> response = executeCall(tmdbApiService.getTopRatedMovies(page, DEFAULT_LANGUAGE));
            cacheMovieListResponse(response);
            try { redisTemplate.opsForValue().set(cacheKey, response, cacheTtlSeconds, TimeUnit.SECONDS); } catch (Exception e) {}
            return response;
        } catch (Exception e) {
            log.error("Error fetching top rated movies from TMDB", e);
            throw new RuntimeException("Failed to fetch top rated movies", e);
        }
    }

    public Map<String, Object> getNowPlayingMovies(Integer page) {
        String cacheKey = "movies:now_playing:" + page;
        try { Object cached = redisTemplate.opsForValue().get(cacheKey); if (cached != null) return convertToMap(cached); } catch (Exception e) {}
        try {
            Map<String, Object> response = executeCall(tmdbApiService.getNowPlayingMovies(page, DEFAULT_LANGUAGE));
            cacheMovieListResponse(response);
            try { redisTemplate.opsForValue().set(cacheKey, response, cacheTtlSeconds, TimeUnit.SECONDS); } catch (Exception e) {}
            return response;
        } catch (Exception e) {
            log.error("Error fetching now playing movies from TMDB", e);
            throw new RuntimeException("Failed to fetch now playing movies", e);
        }
    }

    public Map<String, Object> discoverMovies(Integer page, String sortBy, String withGenres, Integer primaryReleaseYear) {
        String cacheKey = "movies:discover:" + page + ":" + sortBy + ":" + withGenres + ":" + primaryReleaseYear;
        try { Object cached = redisTemplate.opsForValue().get(cacheKey); if (cached != null) return convertToMap(cached); } catch (Exception e) {}
        try {
            Map<String, Object> response = executeCall(tmdbApiService.discoverMovies(page, DEFAULT_LANGUAGE, sortBy, withGenres, primaryReleaseYear));
            cacheMovieListResponse(response);
            try { redisTemplate.opsForValue().set(cacheKey, response, cacheTtlSeconds, TimeUnit.SECONDS); } catch (Exception e) {}
            return response;
        } catch (Exception e) {
            log.error("Error discovering movies", e);
            throw new RuntimeException("Failed to discover movies", e);
        }
    }

    public Map<String, Object> getMovieDetails(Integer movieId) {
        try {
            Map<String, Object> response = executeCall(tmdbApiService.getMovieDetails(movieId, DEFAULT_LANGUAGE));
            cacheMovieDetailResponse(response);
            return response;
        } catch (Exception e) {
            log.error("Error fetching movie details for id: {}", movieId, e);
            throw new RuntimeException("Failed to fetch movie details", e);
        }
    }

    public Map<String, Object> getMovieCredits(Integer movieId) {
        try {
            return executeCall(tmdbApiService.getMovieCredits(movieId, DEFAULT_LANGUAGE));
        } catch (Exception e) {
            log.error("Error fetching movie credits for id: {}", movieId, e);
            throw new RuntimeException("Failed to fetch movie credits", e);
        }
    }

    public Map<String, Object> getMovieImages(Integer movieId) {
        try {
            return executeCall(tmdbApiService.getMovieImages(movieId));
        } catch (Exception e) {
            log.error("Error fetching movie images for id: {}", movieId, e);
            throw new RuntimeException("Failed to fetch movie images", e);
        }
    }

    public Map<String, Object> searchMovies(String query, Integer page) {
        try {
            Map<String, Object> response = executeCall(tmdbApiService.searchMovies(query, page, DEFAULT_LANGUAGE));
            cacheMovieListResponse(response);
            return response;
        } catch (Exception e) {
            log.error("Error searching movies: {}", query, e);
            throw new RuntimeException("Failed to search movies", e);
        }
    }

    @SuppressWarnings("unchecked")
    public void cacheMovieListResponse(Map<String, Object> response) {
        if (response == null) return;
        List<Map<String, Object>> results = (List<Map<String, Object>>) response.get("results");
        if (results == null || results.isEmpty()) return;

        for (Map<String, Object> movieData : results) {
            Movie movie = mapMovie(movieData, false);
            if (movie != null && !movieDao.existsById(movie.getMovieId())) {
                movieDao.insert(movie);
            }
        }
    }

    private void cacheMovieDetailResponse(Map<String, Object> response) {
        Movie movie = mapMovie(response, true);
        if (movie != null) {
            movieDao.saveOrUpdate(movie);
        }
    }

    private Movie mapMovie(Map<String, Object> movieData, boolean fullDetail) {
        Integer movieId = asInteger(movieData.get("id"));
        if (movieId == null) return null;

        List<?> genreIds = movieData.containsKey("genre_ids") ? (List<?>) movieData.get("genre_ids") : new ArrayList<>();
        Object genresValue = movieData.get("genres");

        return Movie.builder()
                .movieId(movieId)
                .title(asString(movieData.get("title")))
                .originalTitle(asString(movieData.get("original_title")))
                .tagline(fullDetail ? asString(movieData.get("tagline")) : null)
                .overview(asString(movieData.get("overview")))
                .posterPath(asString(movieData.get("poster_path")))
                .backdropPath(asString(movieData.get("backdrop_path")))
                .releaseDate(asLocalDate(movieData.get("release_date")))
                .originalLanguage(asString(movieData.get("original_language")))
                .popularity(asBigDecimal(movieData.get("popularity")))
                .voteAverage(asBigDecimal(movieData.get("vote_average")))
                .voteCount(asInteger(movieData.get("vote_count")))
                .adult(asBoolean(movieData.get("adult")))
                .video(asBoolean(movieData.get("video")))
                .runtime(fullDetail ? asInteger(movieData.get("runtime")) : null)
                .budget(fullDetail ? asLong(movieData.get("budget")) : null)
                .revenue(fullDetail ? asLong(movieData.get("revenue")) : null)
                .status(fullDetail ? asString(movieData.get("status")) : null)
                .imdbId(fullDetail ? asString(movieData.get("imdb_id")) : null)
                .homepage(fullDetail ? asString(movieData.get("homepage")) : null)
                .genresJson(genresValue != null ? gson.toJson(genresValue) : (genreIds.isEmpty() ? null : gson.toJson(genreIds)))
                .productionCountriesJson(fullDetail && movieData.get("production_countries") != null ? gson.toJson(movieData.get("production_countries")) : null)
                .spokenLanguagesJson(fullDetail && movieData.get("spoken_languages") != null ? gson.toJson(movieData.get("spoken_languages")) : null)
                .build();
    }

    private Integer asInteger(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.intValue();
        try { return Integer.parseInt(value.toString()); } catch (NumberFormatException ex) { return null; }
    }

    private Long asLong(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.longValue();
        try { return Long.parseLong(value.toString()); } catch (NumberFormatException ex) { return null; }
    }

    private Boolean asBoolean(Object value) {
        if (value == null) return null;
        if (value instanceof Boolean bool) return bool;
        return Boolean.parseBoolean(value.toString());
    }

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }

    private BigDecimal asBigDecimal(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return BigDecimal.valueOf(number.doubleValue());
        try { return new BigDecimal(value.toString()); } catch (NumberFormatException ex) { return null; }
    }

    private LocalDate asLocalDate(Object value) {
        if (value == null) return null;
        String text = value.toString();
        if (text.isBlank()) return null;
        try { return LocalDate.parse(text); } catch (Exception ex) { return null; }
    }

    @SuppressWarnings("unchecked")
    
    public List<Movie> getCachedMovies(int limit, int offset) {
        return movieDao.findAll(limit, offset);
    }

    public List<Movie> getCachedPopularMovies(int limit, int offset) {
        return movieDao.findAll(limit, offset);
    }

    public List<Movie> getCachedTopRatedMovies(int limit, int offset) {
        return movieDao.findTopRated(limit, offset);
    }

    public Movie getCachedMovieById(Integer movieId) {
        return movieDao.findById(movieId).orElse(null);
    }

    public List<Movie> searchCachedMovies(String query, int limit, int offset) {
        return movieDao.findByTitleContaining(query, limit, offset);
    }

    public void syncMovieGenres() {
        try {
            Map<String, Object> response = executeCall(tmdbApiService.getMovieGenres(DEFAULT_LANGUAGE));
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

    @SuppressWarnings("unchecked")
    private Map<String, Object> convertToMap(Object cached) {
        if (cached instanceof Map) {
            return new HashMap<>((Map<String, Object>) cached);
        }
        String json = gson.toJson(cached);
        return gson.fromJson(json, Map.class);
    }
}