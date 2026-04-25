package com.vozflix.controller;

import com.vozflix.api.TmdbApiService;
import com.vozflix.dto.MovieResponse;
import com.vozflix.service.TmdbMovieService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/movies")
@RequiredArgsConstructor
public class MovieController {

    private final TmdbMovieService tmdbMovieService;
    private final TmdbApiService tmdbApiService;

    @GetMapping("/popular")
    public ResponseEntity<Map<String, Object>> getPopularMovies(
            @RequestParam(required = false, defaultValue = "1") Integer page) {
        log.info("Fetching popular movies, page: {}", page);
        Map<String, Object> response = tmdbMovieService.getPopularMovies(page);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/top-rated")
    public ResponseEntity<Map<String, Object>> getTopRatedMovies(
            @RequestParam(required = false, defaultValue = "1") Integer page) {
        log.info("Fetching top rated movies, page: {}", page);
        Map<String, Object> response = tmdbMovieService.getTopRatedMovies(page);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/now-playing")
    public ResponseEntity<Map<String, Object>> getNowPlayingMovies(
            @RequestParam(required = false, defaultValue = "1") Integer page) {
        log.info("Fetching now playing movies, page: {}", page);
        Map<String, Object> response = tmdbMovieService.getNowPlayingMovies(page);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{movieId}")
    public ResponseEntity<Map<String, Object>> getMovieDetails(@PathVariable Integer movieId) {
        log.info("Fetching movie details for id: {}", movieId);
        Map<String, Object> response = tmdbMovieService.getMovieDetails(movieId);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{movieId}/credits")
    public ResponseEntity<Map<String, Object>> getMovieCredits(@PathVariable Integer movieId) {
        log.info("Fetching movie credits for id: {}", movieId);
        Map<String, Object> response = tmdbMovieService.getMovieCredits(movieId);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{movieId}/images")
    public ResponseEntity<Map<String, Object>> getMovieImages(@PathVariable Integer movieId) {
        log.info("Fetching movie images for id: {}", movieId);
        Map<String, Object> response = tmdbMovieService.getMovieImages(movieId);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/search")
    public ResponseEntity<Map<String, Object>> searchMovies(
            @RequestParam String query,
            @RequestParam(required = false, defaultValue = "1") Integer page) {
        log.info("Searching movies: {}", query);
        Map<String, Object> response = tmdbMovieService.searchMovies(query, page);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/discover")
    public ResponseEntity<Map<String, Object>> discoverMovies(
            @RequestParam(required = false, defaultValue = "1") Integer page,
            @RequestParam(required = false) String sortBy,
            @RequestParam(required = false) String withGenres,
            @RequestParam(required = false) Integer primaryReleaseYear) {
        log.info("Discovering movies with filters - page: {}, sortBy: {}, genres: {}", page, sortBy, withGenres);
        try {
            Map<String, Object> response = tmdbApiService.discoverMovies(page, "en-US", sortBy, withGenres, primaryReleaseYear);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error discovering movies", e);
            return ResponseEntity.internalServerError().build();
        }
    }

    @PostMapping("/sync/genres")
    public ResponseEntity<String> syncGenres() {
        log.info("Syncing movie genres from TMDB");
        try {
            tmdbMovieService.syncMovieGenres();
            return ResponseEntity.ok("Genres synced successfully");
        } catch (Exception e) {
            log.error("Error syncing genres", e);
            return ResponseEntity.internalServerError().body("Failed to sync genres");
        }
    }

    @GetMapping("/genres")
    public ResponseEntity<Map<String, Object>> getGenres() {
        log.info("Fetching movie genres");
        try {
            Map<String, Object> response = tmdbApiService.getMovieGenres("en-US");
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error fetching genres", e);
            return ResponseEntity.internalServerError().build();
        }
    }
}