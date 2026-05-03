package com.vozflix.controller;

import com.vozflix.dao.WatchlistDao;
import com.vozflix.entity.WatchlistItem;
import com.vozflix.entity.WatchlistItem.ContentType;
import com.vozflix.entity.WatchlistItem.WatchlistStatus;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@RestController
@RequestMapping("/api/watchlist")
@RequiredArgsConstructor
public class WatchlistController {

    private final WatchlistDao watchlistDao;

    @PostMapping("/add")
    public ResponseEntity<Map<String, Object>> addItem(@RequestBody Map<String, Object> body) {
        try {
            Integer userId = (Integer) body.get("userId");
            String contentTypeStr = (String) body.get("contentType");
            Integer tmdbId = (Integer) body.get("tmdbId");
            String statusStr = (String) body.get("status");

            if (userId == null || tmdbId == null) {
                Map<String, Object> error = new HashMap<>();
                error.put("error", "userId and tmdbId are required");
                return ResponseEntity.badRequest().body(error);
            }

            ContentType contentType = ContentType.valueOf(contentTypeStr != null ? contentTypeStr.toUpperCase() : "MOVIE");
            WatchlistStatus status = WatchlistStatus.valueOf(statusStr != null ? statusStr.toUpperCase() : "WISHLIST");

            boolean exists = watchlistDao.existsByUserIdAndTmdbIdAndContentType(userId, tmdbId, contentType);
            if (exists) {
                watchlistDao.deleteByUserIdAndTmdbIdAndContentType(userId, tmdbId, contentType);
            }

            WatchlistItem item = WatchlistItem.builder()
                    .userId(userId)
                    .contentType(contentType)
                    .tmdbId(tmdbId)
                    .status(status)
                    .progressSeconds(0)
                    .currentEpisode(1)
                    .currentSeason(1)
                    .isBookmarked(true)
                    .build();

            watchlistDao.insert(item);

            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("action", exists ? "removed" : "added");
            response.put("item", watchlistItemToMap(item));
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error adding watchlist item", e);
            Map<String, Object> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.internalServerError().body(error);
        }
    }

    @PostMapping("/update")
    public ResponseEntity<Map<String, Object>> updateItem(@RequestBody Map<String, Object> body) {
        try {
            Integer watchlistId = (Integer) body.get("watchlistId");
            String statusStr = (String) body.get("status");
            Integer progressSeconds = (Integer) body.get("progressSeconds");

            if (watchlistId == null) {
                Map<String, Object> error = new HashMap<>();
                error.put("error", "watchlistId is required");
                return ResponseEntity.badRequest().body(error);
            }

            WatchlistItem item = watchlistDao.findById(watchlistId).orElse(null);
            if (item == null) {
                Map<String, Object> error = new HashMap<>();
                error.put("error", "Item not found");
                return ResponseEntity.notFound().build();
            }

            if (statusStr != null) {
                item.setStatus(WatchlistStatus.valueOf(statusStr.toUpperCase()));
            }
            if (progressSeconds != null) {
                item.setProgressSeconds(progressSeconds);
            }

            watchlistDao.update(item);

            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("item", watchlistItemToMap(item));
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error updating watchlist item", e);
            Map<String, Object> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.internalServerError().body(error);
        }
    }

    @GetMapping("/{userId}")
    public ResponseEntity<Map<String, Object>> getUserWatchlist(@PathVariable Integer userId) {
        try {
            List<WatchlistItem> items = watchlistDao.findByUserId(userId);
            List<Map<String, Object>> itemMaps = items.stream().map(this::watchlistItemToMap).collect(Collectors.toList());

            Map<String, Object> response = new HashMap<>();
            response.put("items", itemMaps);
            response.put("total", items.size());
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error fetching watchlist for user {}", userId, e);
            Map<String, Object> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.internalServerError().body(error);
        }
    }

    @GetMapping("/{userId}/{status}")
    public ResponseEntity<Map<String, Object>> getUserWatchlistByStatus(@PathVariable Integer userId, @PathVariable String status) {
        try {
            WatchlistStatus watchlistStatus = WatchlistStatus.valueOf(status.toUpperCase());
            List<WatchlistItem> items = watchlistDao.findByUserIdAndStatus(userId, watchlistStatus);
            List<Map<String, Object>> itemMaps = items.stream().map(this::watchlistItemToMap).collect(Collectors.toList());

            Map<String, Object> response = new HashMap<>();
            response.put("items", itemMaps);
            response.put("total", items.size());
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error fetching watchlist for user {} with status {}", userId, status, e);
            Map<String, Object> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.internalServerError().body(error);
        }
    }

    @DeleteMapping("/{watchlistId}")
    public ResponseEntity<Map<String, Object>> deleteItem(@PathVariable Integer watchlistId) {
        try {
            watchlistDao.deleteById(watchlistId);
            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            log.error("Error deleting watchlist item {}", watchlistId, e);
            Map<String, Object> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.internalServerError().body(error);
        }
    }

    private Map<String, Object> watchlistItemToMap(WatchlistItem item) {
        Map<String, Object> map = new HashMap<>();
        map.put("watchlistId", item.getWatchlistId());
        map.put("userId", item.getUserId());
        map.put("contentType", item.getContentType().name().toLowerCase());
        map.put("tmdbId", item.getTmdbId());
        map.put("status", item.getStatus().name().toLowerCase());
        map.put("progressSeconds", item.getProgressSeconds());
        map.put("currentEpisode", item.getCurrentEpisode());
        map.put("currentSeason", item.getCurrentSeason());
        map.put("rating", item.getRating());
        map.put("review", item.getReview());
        map.put("isBookmarked", item.getIsBookmarked());
        return map;
    }
}
