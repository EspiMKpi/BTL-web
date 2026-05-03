package com.vozflix.service;

import com.google.gson.Gson;
import com.vozflix.api.TmdbApiService;
import lombok.RequiredArgsConstructor;
import java.util.ArrayList;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import retrofit2.Call;
import retrofit2.Response;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class SearchCacheService {

        private final TmdbApiService tmdbApiService;
    private final TmdbMovieService tmdbMovieService;
    private final TmdbSeriesService tmdbSeriesService;
    private final RedisTemplate<String, Object> redisTemplate;
    private final Gson gson;

    @Value("${search.cache.ttl:3600}")
    private long cacheTtlSeconds;

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
            log.warn("Redis cache read error for search: {}", query);
        }

        log.debug("Cache miss for search: {}, fetching from TMDB", query);
        Map<String, Object> result = executeCall(tmdbApiService.searchMulti(query, page, DEFAULT_LANGUAGE));

        if (result != null && result.containsKey("results")) {
            List<Map<String, Object>> results = (List<Map<String, Object>>) result.get("results");
            List<Map<String, Object>> movies = new ArrayList<>();
            List<Map<String, Object>> series = new ArrayList<>();
            for (Map<String, Object> item : results) {
                if ("movie".equals(item.get("media_type"))) movies.add(item);
                else if ("tv".equals(item.get("media_type"))) series.add(item);
            }
            if (!movies.isEmpty()) {
                Map<String, Object> movieRes = new HashMap<>();
                movieRes.put("results", movies);
                tmdbMovieService.cacheMovieListResponse(movieRes);
            }
            if (!series.isEmpty()) {
                Map<String, Object> seriesRes = new HashMap<>();
                seriesRes.put("results", series);
                tmdbSeriesService.cacheSeriesListResponse(seriesRes);
            }
        }

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
                return convertToMap(cached);
            }
        } catch (Exception e) {
            log.warn("Redis cache read error for search movies: {}", query);
        }

        Map<String, Object> result = tmdbMovieService.searchMovies(query, page);
        try {
            redisTemplate.opsForValue().set(cacheKey, result, cacheTtlSeconds, TimeUnit.SECONDS);
        } catch (Exception e) {}
        return result;
    }

    public Map<String, Object> searchSeries(String query, Integer page) {
        String cacheKey = buildCacheKey(SEARCH_SERIES_KEY_PREFIX, query, page);
        try {
            Object cached = redisTemplate.opsForValue().get(cacheKey);
            if (cached != null) {
                return convertToMap(cached);
            }
        } catch (Exception e) {
            log.warn("Redis cache read error for search series: {}", query);
        }

        Map<String, Object> result = tmdbSeriesService.searchTvShows(query, page);
        try {
            redisTemplate.opsForValue().set(cacheKey, result, cacheTtlSeconds, TimeUnit.SECONDS);
        } catch (Exception e) {}
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