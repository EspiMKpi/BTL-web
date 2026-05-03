package com.vozflix.controller;

import com.vozflix.api.TmdbApiService;
import com.vozflix.dao.GenreDao;
import com.vozflix.service.TmdbSeriesService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/series")
@RequiredArgsConstructor
public class SeriesController {

    private final TmdbSeriesService tmdbSeriesService;
    private final TmdbApiService tmdbApiService;
    private final GenreDao genreDao;

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
            Map<String, Object> response = tmdbSeriesService.discoverTvShows(page, sortBy, withGenres);
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

    @PostMapping("/sync/all")
    public ResponseEntity<String> syncAll() {
        log.info("Starting full TV sync");
        try {
            tmdbSeriesService.syncTvGenres();
            tmdbSeriesService.getPopularTvShows(1);
            tmdbSeriesService.getTopRatedTvShows(1);
            return ResponseEntity.ok("Full TV sync completed successfully");
        } catch (Exception e) {
            log.error("Error during full TV sync", e);
            return ResponseEntity.internalServerError().body("Failed to sync: " + e.getMessage());
        }
    }

    @GetMapping("/genres")
    public ResponseEntity<Map<String, Object>> getGenres() {
        log.info("Fetching TV genres from MySQL");
        try {
            List<com.vozflix.entity.Genre> genres = genreDao.findAll();
            if (genres.isEmpty()) {
                Map<String, Object> response = tmdbApiService.getTvGenres("en-US").execute().body();
                return ResponseEntity.ok(response);
            }
            List<Map<String, Object>> genreList = new ArrayList<>();
            for (com.vozflix.entity.Genre g : genres) {
                Map<String, Object> map = new HashMap<>();
                map.put("id", g.getGenreId());
                map.put("name", g.getName());
                genreList.add(map);
            }
            Map<String, Object> response = new HashMap<>();
            response.put("genres", genreList);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error fetching genres", e);
            return ResponseEntity.internalServerError().build();
        }
    }

    @GetMapping("/cached")
    public ResponseEntity<Map<String, Object>> getCachedSeries(
            @RequestParam(required = false, defaultValue = "20") Integer limit,
            @RequestParam(required = false, defaultValue = "0") Integer offset) {
        log.info("Fetching cached series, limit: {}, offset: {}", limit, offset);
        try {
            List<com.vozflix.entity.Series> series = tmdbSeriesService.getCachedSeries(limit, offset);
            List<Map<String, Object>> results = new ArrayList<>();
            for (com.vozflix.entity.Series s : series) {
                Map<String, Object> map = new HashMap<>();
                map.put("id", s.getSeriesId());
                map.put("name", s.getName());
                map.put("overview", s.getOverview());
                map.put("poster_path", s.getPosterPath());
                map.put("backdrop_path", s.getBackdropPath());
                map.put("first_air_date", s.getFirstAirDate());
                map.put("vote_average", s.getVoteAverage());
                map.put("popularity", s.getPopularity());
                map.put("number_of_seasons", s.getNumberOfSeasons());
                map.put("number_of_episodes", s.getNumberOfEpisodes());
                results.add(map);
            }
            Map<String, Object> response = new HashMap<>();
            response.put("results", results);
            response.put("total", tmdbSeriesService.getCachedSeries(Integer.MAX_VALUE, 0).size());
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error fetching cached series", e);
            return ResponseEntity.internalServerError().build();
        }
    }
}