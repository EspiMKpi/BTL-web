package com.vozflix.controller;

import com.vozflix.service.SearchCacheService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/search")
@RequiredArgsConstructor
public class SearchController {

    private final SearchCacheService searchCacheService;

    @GetMapping
    public ResponseEntity<Map<String, Object>> search(
            @RequestParam String query,
            @RequestParam(required = false, defaultValue = "1") Integer page) {
        log.info("Searching for: {}", query);
        try {
            Map<String, Object> response = searchCacheService.search(query, page);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error searching: {}", query, e);
            return ResponseEntity.internalServerError().build();
        }
    }

    @GetMapping("/movies")
    public ResponseEntity<Map<String, Object>> searchMovies(
            @RequestParam String query,
            @RequestParam(required = false, defaultValue = "1") Integer page) {
        log.info("Searching movies only: {}", query);
        try {
            Map<String, Object> response = searchCacheService.searchMovies(query, page);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error searching movies: {}", query, e);
            return ResponseEntity.internalServerError().build();
        }
    }

    @GetMapping("/series")
    public ResponseEntity<Map<String, Object>> searchSeries(
            @RequestParam String query,
            @RequestParam(required = false, defaultValue = "1") Integer page) {
        log.info("Searching series only: {}", query);
        try {
            Map<String, Object> response = searchCacheService.searchSeries(query, page);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error searching series: {}", query, e);
            return ResponseEntity.internalServerError().build();
        }
    }
}