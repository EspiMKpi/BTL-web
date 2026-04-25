package com.vozflix.service;

import com.google.gson.Gson;
import com.vozflix.api.TmdbApiService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class SearchCacheService {

    private final TmdbApiService tmdbApiService;
    private final RedisTemplate<String, Object> redisTemplate;
    private final Gson gson;

    @Value("${search.cache.ttl:3600}")
    private long cacheTtlSeconds;

    private static final String DEFAULT_LANGUAGE = "en-US";

    private static final String SEARCH_KEY_PREFIX = "search:";
    private static final String SEARCH_MOVIES_KEY_PREFIX = "search:movies:";
    private static final String SEARCH_SERIES_KEY_PREFIX = "search:series:";

    public Map<String, Object> search(String query, Integer page) {
        String cacheKey = buildCacheKey(SEARCH_KEY_PREFIX, query, page);

        try {
            Object cached = redisTemplate.opsForValue().get(cacheKey);
            if (cached != null) {
                log.debug("Cache hit for search: {}", query);
                return convertToMap(cached);
            }
        } catch (Exception e) {
            log.warn("Redis cache read error for search: {}, falling back to API", query);
        }

        log.debug("Cache miss for search: {}, fetching from TMDB", query);
        Map<String, Object> result = tmdbApiService.searchMulti(query, page, DEFAULT_LANGUAGE);

        try {
            redisTemplate.opsForValue().set(cacheKey, result, cacheTtlSeconds, TimeUnit.SECONDS);
        } catch (Exception e) {
            log.warn("Failed to cache search results for: {}", query);
        }

        return result;
    }

    public Map<String, Object> searchMovies(String query, Integer page) {
        String cacheKey = buildCacheKey(SEARCH_MOVIES_KEY_PREFIX, query, page);

        try {
            Object cached = redisTemplate.opsForValue().get(cacheKey);
            if (cached != null) {
                log.debug("Cache hit for search movies: {}", query);
                return convertToMap(cached);
            }
        } catch (Exception e) {
            log.warn("Redis cache read error for search movies: {}, falling back to API", query);
        }

        log.debug("Cache miss for search movies: {}, fetching from TMDB", query);
        Map<String, Object> result = tmdbApiService.searchMovies(query, page, DEFAULT_LANGUAGE);

        try {
            redisTemplate.opsForValue().set(cacheKey, result, cacheTtlSeconds, TimeUnit.SECONDS);
        } catch (Exception e) {
            log.warn("Failed to cache search movies results for: {}", query);
        }

        return result;
    }

    public Map<String, Object> searchSeries(String query, Integer page) {
        String cacheKey = buildCacheKey(SEARCH_SERIES_KEY_PREFIX, query, page);

        try {
            Object cached = redisTemplate.opsForValue().get(cacheKey);
            if (cached != null) {
                log.debug("Cache hit for search series: {}", query);
                return convertToMap(cached);
            }
        } catch (Exception e) {
            log.warn("Redis cache read error for search series: {}, falling back to API", query);
        }

        log.debug("Cache miss for search series: {}, fetching from TMDB", query);
        Map<String, Object> result = tmdbApiService.searchTvShows(query, page, DEFAULT_LANGUAGE);

        try {
            redisTemplate.opsForValue().set(cacheKey, result, cacheTtlSeconds, TimeUnit.SECONDS);
        } catch (Exception e) {
            log.warn("Failed to cache search series results for: {}", query);
        }

        return result;
    }

    public void invalidateCache(String query) {
        try {
            String pattern = "*search*" + query.toLowerCase() + "*";
            var keys = redisTemplate.keys(pattern);
            if (keys != null && !keys.isEmpty()) {
                redisTemplate.delete(keys);
                log.debug("Cleared {} cache entries for query: {}", keys.size(), query);
            }
        } catch (Exception e) {
            log.warn("Failed to invalidate cache for query: {}", query);
        }
    }

    private String buildCacheKey(String prefix, String query, Integer page) {
        return prefix + query.toLowerCase().replace(" ", "_") + ":" + page;
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