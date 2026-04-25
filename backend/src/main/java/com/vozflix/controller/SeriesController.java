package com.vozflix.controller;

import com.vozflix.api.TmdbApiService;
import com.vozflix.service.TmdbSeriesService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/series")
@RequiredArgsConstructor
public class SeriesController {

    private final TmdbSeriesService tmdbSeriesService;
    private final TmdbApiService tmdbApiService;

    @GetMapping("/popular")
    public ResponseEntity<Map<String, Object>> getPopularTvShows(
            @RequestParam(required = false, defaultValue = "1") Integer page) {
        log.info("Fetching popular TV shows, page: {}", page);
        Map<String, Object> response = tmdbSeriesService.getPopularTvShows(page);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/top-rated")
    public ResponseEntity<Map<String, Object>> getTopRatedTvShows(
            @RequestParam(required = false, defaultValue = "1") Integer page) {
        log.info("Fetching top rated TV shows, page: {}", page);
        Map<String, Object> response = tmdbSeriesService.getTopRatedTvShows(page);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{tvId}")
    public ResponseEntity<Map<String, Object>> getTvShowDetails(@PathVariable Integer tvId) {
        log.info("Fetching TV show details for id: {}", tvId);
        Map<String, Object> response = tmdbSeriesService.getTvShowDetails(tvId);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{tvId}/season/{seasonNumber}")
    public ResponseEntity<Map<String, Object>> getSeasonDetails(
            @PathVariable Integer tvId,
            @PathVariable Integer seasonNumber) {
        log.info("Fetching season details for TV id: {}, season: {}", tvId, seasonNumber);
        Map<String, Object> response = tmdbSeriesService.getSeasonDetails(tvId, seasonNumber);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/{tvId}/credits")
    public ResponseEntity<Map<String, Object>> getTvShowCredits(@PathVariable Integer tvId) {
        log.info("Fetching TV show credits for id: {}", tvId);
        Map<String, Object> response = tmdbSeriesService.getTvShowCredits(tvId);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/search")
    public ResponseEntity<Map<String, Object>> searchTvShows(
            @RequestParam String query,
            @RequestParam(required = false, defaultValue = "1") Integer page) {
        log.info("Searching TV shows: {}", query);
        Map<String, Object> response = tmdbSeriesService.searchTvShows(query, page);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/discover")
    public ResponseEntity<Map<String, Object>> discoverTvShows(
            @RequestParam(required = false, defaultValue = "1") Integer page,
            @RequestParam(required = false) String sortBy,
            @RequestParam(required = false) String withGenres) {
        log.info("Discovering TV shows with filters - page: {}, sortBy: {}, genres: {}", page, sortBy, withGenres);
        try {
            Map<String, Object> response = tmdbApiService.discoverTvShows(page, "en-US", sortBy, withGenres);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error discovering TV shows", e);
            return ResponseEntity.internalServerError().build();
        }
    }

    @PostMapping("/sync/genres")
    public ResponseEntity<String> syncGenres() {
        log.info("Syncing TV genres from TMDB");
        try {
            tmdbSeriesService.syncTvGenres();
            return ResponseEntity.ok("Genres synced successfully");
        } catch (Exception e) {
            log.error("Error syncing genres", e);
            return ResponseEntity.internalServerError().body("Failed to sync genres");
        }
    }

    @GetMapping("/genres")
    public ResponseEntity<Map<String, Object>> getGenres() {
        log.info("Fetching TV genres");
        try {
            Map<String, Object> response = tmdbApiService.getTvGenres("en-US");
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error fetching genres", e);
            return ResponseEntity.internalServerError().build();
        }
    }
}