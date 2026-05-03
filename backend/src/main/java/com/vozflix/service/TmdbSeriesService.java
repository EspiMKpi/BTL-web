package com.vozflix.service;

import com.google.gson.Gson;
import com.vozflix.api.TmdbApiService;
import com.vozflix.dao.EpisodeDao;
import com.vozflix.dao.GenreDao;
import com.vozflix.dao.SeriesDao;
import com.vozflix.entity.Genre;
import com.vozflix.entity.Series;
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
import java.util.List;
import java.util.Map;
import java.util.HashMap;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class TmdbSeriesService {

    private final TmdbApiService tmdbApiService;
    private final SeriesDao seriesDao;
    private final EpisodeDao episodeDao;
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

    public Map<String, Object> discoverTvShows(Integer page, String sortBy, String withGenres) {
        String cacheKey = "series:discover:" + page + ":" + sortBy + ":" + withGenres;
        try { Object cached = redisTemplate.opsForValue().get(cacheKey); if (cached != null) return convertToMap(cached); } catch (Exception e) {}
        try {
            Map<String, Object> response = executeCall(tmdbApiService.discoverTvShows(page, DEFAULT_LANGUAGE, sortBy, withGenres));
            cacheSeriesListResponse(response);
            try { redisTemplate.opsForValue().set(cacheKey, response, cacheTtlSeconds, TimeUnit.SECONDS); } catch (Exception e) {}
            return response;
        } catch (Exception e) {
            log.error("Error discovering TV shows", e);
            throw new RuntimeException("Failed to discover TV shows", e);
        }
    }

    public Map<String, Object> getTvShowCredits(Integer tvId) {
        try {
            return executeCall(tmdbApiService.getTvShowCredits(tvId, DEFAULT_LANGUAGE));
        } catch (Exception e) {
            log.error("Error fetching TV show credits for id: {}", tvId, e);
            throw new RuntimeException("Failed to fetch TV show credits", e);
        }
    }

    public Map<String, Object> searchTvShows(String query, Integer page) {
        try {
            Map<String, Object> response = executeCall(tmdbApiService.searchTvShows(query, page, DEFAULT_LANGUAGE));
            cacheSeriesListResponse(response);
            return response;
        } catch (Exception e) {
            log.error("Error searching TV shows: {}", query, e);
            throw new RuntimeException("Failed to search TV shows", e);
        }
    }

    @SuppressWarnings("unchecked")
    public void cacheSeriesListResponse(Map<String, Object> response) {
        if (response == null) {
            return;
        }

        List<Map<String, Object>> results = (List<Map<String, Object>>) response.get("results");
        if (results == null || results.isEmpty()) {
            return;
        }

        for (Map<String, Object> seriesData : results) {
            Series series = mapSeries(seriesData, false);
            if (series != null && !seriesDao.existsById(series.getSeriesId())) {
                seriesDao.insert(series);
            }
        }
    }

    private void cacheSeriesDetailResponse(Map<String, Object> response) {
        Series series = mapSeries(response, true);
        if (series != null) {
            seriesDao.saveOrUpdate(series);
        }
    }

    private Series mapSeries(Map<String, Object> seriesData, boolean fullDetail) {
        Integer seriesId = asInteger(seriesData.get("id"));
        if (seriesId == null) {
            return null;
        }

        List<?> genreIds = seriesData.containsKey("genre_ids") ? (List<?>) seriesData.get("genre_ids") : new ArrayList<>();
        Object genresValue = seriesData.get("genres");

        return Series.builder()
                .seriesId(seriesId)
                .name(asString(seriesData.get("name")))
                .originalName(asString(seriesData.get("original_name")))
                .tagline(fullDetail ? asString(seriesData.get("tagline")) : null)
                .overview(asString(seriesData.get("overview")))
                .posterPath(asString(seriesData.get("poster_path")))
                .backdropPath(asString(seriesData.get("backdrop_path")))
                .firstAirDate(asLocalDate(seriesData.get("first_air_date")))
                .lastAirDate(fullDetail ? asLocalDate(seriesData.get("last_air_date")) : null)
                .originalLanguage(asString(seriesData.get("original_language")))
                .popularity(asBigDecimal(seriesData.get("popularity")))
                .voteAverage(asBigDecimal(seriesData.get("vote_average")))
                .voteCount(asInteger(seriesData.get("vote_count")))
                .adult(asBoolean(seriesData.get("adult")))
                .episodeRunTimeJson(fullDetail && seriesData.get("episode_run_time") != null ? gson.toJson(seriesData.get("episode_run_time")) : null)
                .type(fullDetail ? asString(seriesData.get("type")) : null)
                .status(fullDetail ? asString(seriesData.get("status")) : null)
                .imdbId(fullDetail ? asString(seriesData.get("imdb_id")) : null)
                .homepage(fullDetail ? asString(seriesData.get("homepage")) : null)
                .genresJson(genresValue != null ? gson.toJson(genresValue) : (genreIds.isEmpty() ? null : gson.toJson(genreIds)))
                .networksJson(fullDetail && seriesData.get("networks") != null ? gson.toJson(seriesData.get("networks")) : null)
                .productionCountriesJson(fullDetail && seriesData.get("production_countries") != null ? gson.toJson(seriesData.get("production_countries")) : null)
                .spokenLanguagesJson(fullDetail && seriesData.get("spoken_languages") != null ? gson.toJson(seriesData.get("spoken_languages")) : null)
                .numberOfSeasons(fullDetail ? asInteger(seriesData.get("number_of_seasons")) : null)
                .numberOfEpisodes(fullDetail ? asInteger(seriesData.get("number_of_episodes")) : null)
                .build();
    }

    private Integer asInteger(Object value) {
        if (value == null) {
            return null;
        }

        if (value instanceof Number number) {
            return number.intValue();
        }

        try {
            return Integer.parseInt(value.toString());
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private Boolean asBoolean(Object value) {
        if (value == null) {
            return null;
        }

        if (value instanceof Boolean bool) {
            return bool;
        }

        return Boolean.parseBoolean(value.toString());
    }

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }

    private BigDecimal asBigDecimal(Object value) {
        if (value == null) {
            return null;
        }

        if (value instanceof Number number) {
            return BigDecimal.valueOf(number.doubleValue());
        }

        try {
            return new BigDecimal(value.toString());
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private LocalDate asLocalDate(Object value) {
        if (value == null) {
            return null;
        }

        String text = value.toString();
        if (text.isBlank()) {
            return null;
        }

        try {
            return LocalDate.parse(text);
        } catch (Exception ex) {
            return null;
        }
    }

    @SuppressWarnings("unchecked")
    public void syncTvGenres() {
        try {
            Map<String, Object> response = executeCall(tmdbApiService.getTvGenres(DEFAULT_LANGUAGE));
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
            log.error("Error syncing TV genres", e);
            throw new RuntimeException("Failed to sync genres", e);
        }
    }

    public List<Series> getCachedSeries(int limit, int offset) {
        return seriesDao.findAll(limit, offset);
    }

    public List<Series> getCachedPopularSeries(int limit, int offset) {
        return seriesDao.findAll(limit, offset);
    }

    public List<Series> getCachedTopRatedSeries(int limit, int offset) {
        return seriesDao.findAll(limit, offset);
    }

    public Series getCachedSeriesById(Integer seriesId) {
        return seriesDao.findById(seriesId).orElse(null);
    }

    public List<Series> searchCachedSeries(String query, int limit, int offset) {
        return seriesDao.findByNameContaining(query, limit, offset);
    }

    public Map<String, Object> getPopularTvShows(Integer page) {
        String cacheKey = "series:popular:" + page;
        try { Object cached = redisTemplate.opsForValue().get(cacheKey); if (cached != null) return convertToMap(cached); } catch (Exception e) {}
        try {
            Map<String, Object> response = executeCall(tmdbApiService.getPopularTvShows(page, DEFAULT_LANGUAGE));
            cacheSeriesListResponse(response);
            try { redisTemplate.opsForValue().set(cacheKey, response, cacheTtlSeconds, TimeUnit.SECONDS); } catch (Exception e) {}
            return response;
        } catch (Exception e) {
            log.error("Error fetching popular TV shows from TMDB", e);
            throw new RuntimeException("Failed to fetch popular TV shows", e);
        }
    }

    public Map<String, Object> getTopRatedTvShows(Integer page) {
        String cacheKey = "series:top_rated:" + page;
        try { Object cached = redisTemplate.opsForValue().get(cacheKey); if (cached != null) return convertToMap(cached); } catch (Exception e) {}
        try {
            Map<String, Object> response = executeCall(tmdbApiService.getTopRatedTvShows(page, DEFAULT_LANGUAGE));
            cacheSeriesListResponse(response);
            try { redisTemplate.opsForValue().set(cacheKey, response, cacheTtlSeconds, TimeUnit.SECONDS); } catch (Exception e) {}
            return response;
        } catch (Exception e) {
            log.error("Error fetching top rated TV shows from TMDB", e);
            throw new RuntimeException("Failed to fetch top rated TV shows", e);
        }
    }

    public Map<String, Object> getTvShowDetails(Integer tvId) {
        try {
            Series cached = seriesDao.findById(tvId).orElse(null);
            if (cached != null) {
                return buildSeriesDetailResponse(cached);
            }
            Map<String, Object> response = executeCall(tmdbApiService.getTvShowDetails(tvId, DEFAULT_LANGUAGE));
            cacheSeriesDetailResponse(response);
            return response;
        } catch (Exception e) {
            log.error("Error fetching TV show details for id: {}", tvId, e);
            throw new RuntimeException("Failed to fetch TV show details", e);
        }
    }

    public Map<String, Object> getSeasonDetails(Integer tvId, Integer seasonNumber) {
        try {
            List<Map<String, Object>> episodes = getCachedEpisodes(tvId, seasonNumber);
            if (!episodes.isEmpty()) {
                Series series = seriesDao.findById(tvId).orElse(null);
                Map<String, Object> response = new java.util.HashMap<>();
                response.put("id", tvId);
                response.put("name", series != null ? series.getName() : "");
                response.put("season_number", seasonNumber);
                response.put("episodes", episodes);
                return response;
            }
            return executeCall(tmdbApiService.getSeasonDetails(tvId, seasonNumber, DEFAULT_LANGUAGE));
        } catch (Exception e) {
            log.error("Error fetching season details for TV id: {}, season: {}", tvId, seasonNumber, e);
            throw new RuntimeException("Failed to fetch season details", e);
        }
    }

    private List<Map<String, Object>> getCachedEpisodes(Integer seriesId, Integer seasonNumber) {
        try {
            List<com.vozflix.entity.Episode> episodes = episodeDao.findBySeason(seriesId, seasonNumber);
            return episodes.stream().map(this::episodeToMap).toList();
        } catch (Exception e) {
            log.warn("No cached episodes for series {} season {}", seriesId, seasonNumber);
            return new ArrayList<>();
        }
    }

    private Map<String, Object> episodeToMap(com.vozflix.entity.Episode episode) {
        Map<String, Object> map = new java.util.HashMap<>();
        map.put("id", episode.getEpisodeId());
        map.put("episode_number", episode.getEpisodeNumber());
        map.put("season_number", episode.getSeasonNumber());
        map.put("name", episode.getName());
        map.put("overview", episode.getOverview());
        map.put("still_path", episode.getStillPath());
        map.put("air_date", episode.getAirDate());
        map.put("runtime", episode.getRuntime());
        map.put("vote_average", episode.getVoteAverage());
        map.put("vote_count", episode.getVoteCount());
        return map;
    }

    private Map<String, Object> buildSeriesListResponse(List<Series> series, Integer page) {
        List<Map<String, Object>> results = series.stream().map(this::seriesToMap).toList();
        Map<String, Object> response = new java.util.HashMap<>();
        response.put("page", page);
        response.put("results", results);
        response.put("total_pages", 1);
        response.put("total_results", series.size());
        return response;
    }

    private Map<String, Object> buildSeriesDetailResponse(Series series) {
        Map<String, Object> map = new java.util.HashMap<>();
        map.put("id", series.getSeriesId());
        map.put("name", series.getName());
        map.put("original_name", series.getOriginalName());
        map.put("tagline", series.getTagline());
        map.put("overview", series.getOverview());
        map.put("poster_path", series.getPosterPath());
        map.put("backdrop_path", series.getBackdropPath());
        map.put("first_air_date", series.getFirstAirDate());
        map.put("last_air_date", series.getLastAirDate());
        map.put("original_language", series.getOriginalLanguage());
        map.put("popularity", series.getPopularity());
        map.put("vote_average", series.getVoteAverage());
        map.put("vote_count", series.getVoteCount());
        map.put("adult", series.getAdult());
        map.put("type", series.getType());
        map.put("status", series.getStatus());
        map.put("imdb_id", series.getImdbId());
        map.put("homepage", series.getHomepage());
        map.put("number_of_seasons", series.getNumberOfSeasons());
        map.put("number_of_episodes", series.getNumberOfEpisodes());
        if (series.getGenresJson() != null) {
            try {
                map.put("genres", gson.fromJson(series.getGenresJson(), List.class));
            } catch (Exception e) {
                log.warn("Failed to parse genres_json for series {}", series.getSeriesId());
            }
        }
        if (series.getNetworksJson() != null) {
            try {
                map.put("networks", gson.fromJson(series.getNetworksJson(), List.class));
            } catch (Exception e) {
                log.warn("Failed to parse networks_json for series {}", series.getSeriesId());
            }
        }
        if (series.getSpokenLanguagesJson() != null) {
            try {
                map.put("spoken_languages", gson.fromJson(series.getSpokenLanguagesJson(), List.class));
            } catch (Exception e) {
                log.warn("Failed to parse spoken_languages_json for series {}", series.getSeriesId());
            }
        }
        return map;
    }

    private Map<String, Object> seriesToMap(Series series) {
        Map<String, Object> map = new java.util.HashMap<>();
        map.put("id", series.getSeriesId());
        map.put("name", series.getName());
        map.put("overview", series.getOverview());
        map.put("poster_path", series.getPosterPath());
        map.put("backdrop_path", series.getBackdropPath());
        map.put("first_air_date", series.getFirstAirDate());
        map.put("original_language", series.getOriginalLanguage());
        map.put("popularity", series.getPopularity());
        map.put("vote_average", series.getVoteAverage());
        map.put("vote_count", series.getVoteCount());
        map.put("adult", series.getAdult());
        if (series.getGenresJson() != null) {
            try {
                map.put("genre_ids", gson.fromJson(series.getGenresJson(), List.class));
            } catch (Exception e) {
                log.warn("Failed to parse genres_json for series {}", series.getSeriesId());
            }
        }
        return map;
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
