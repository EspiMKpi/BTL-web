package com.vozflix.service;

import com.google.gson.Gson;
import com.vozflix.api.TmdbApiService;
import com.vozflix.dao.GenreDao;
import com.vozflix.dao.SeriesDao;
import com.vozflix.entity.Genre;
import com.vozflix.entity.Series;
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
public class TmdbSeriesService {

    private final TmdbApiService tmdbApiService;
    private final SeriesDao seriesDao;
    private final GenreDao genreDao;
    private final Gson gson;

    @Value("${tmdb.api.image-base-url:https://image.tmdb.org/t/p}")
    private String imageBaseUrl;

    private static final String DEFAULT_LANGUAGE = "en-US";

    public Map<String, Object> getPopularTvShows(Integer page) {
        try {
            return tmdbApiService.getPopularTvShows(page, DEFAULT_LANGUAGE);
        } catch (Exception e) {
            log.error("Error fetching popular TV shows from TMDB", e);
            throw new RuntimeException("Failed to fetch popular TV shows", e);
        }
    }

    public Map<String, Object> getTopRatedTvShows(Integer page) {
        try {
            return tmdbApiService.getTopRatedTvShows(page, DEFAULT_LANGUAGE);
        } catch (Exception e) {
            log.error("Error fetching top rated TV shows from TMDB", e);
            throw new RuntimeException("Failed to fetch top rated TV shows", e);
        }
    }

    public Map<String, Object> getTvShowDetails(Integer tvId) {
        try {
            return tmdbApiService.getTvShowDetails(tvId, DEFAULT_LANGUAGE);
        } catch (Exception e) {
            log.error("Error fetching TV show details for id: {}", tvId, e);
            throw new RuntimeException("Failed to fetch TV show details", e);
        }
    }

    public Map<String, Object> getSeasonDetails(Integer tvId, Integer seasonNumber) {
        try {
            return tmdbApiService.getSeasonDetails(tvId, seasonNumber, DEFAULT_LANGUAGE);
        } catch (Exception e) {
            log.error("Error fetching season details for TV id: {}, season: {}", tvId, seasonNumber, e);
            throw new RuntimeException("Failed to fetch season details", e);
        }
    }

    public Map<String, Object> getTvShowCredits(Integer tvId) {
        try {
            return tmdbApiService.getTvShowCredits(tvId, DEFAULT_LANGUAGE);
        } catch (Exception e) {
            log.error("Error fetching TV show credits for id: {}", tvId, e);
            throw new RuntimeException("Failed to fetch TV show credits", e);
        }
    }

    public Map<String, Object> searchTvShows(String query, Integer page) {
        try {
            return tmdbApiService.searchTvShows(query, page, DEFAULT_LANGUAGE);
        } catch (Exception e) {
            log.error("Error searching TV shows: {}", query, e);
            throw new RuntimeException("Failed to search TV shows", e);
        }
    }

    @SuppressWarnings("unchecked")
    public void syncTvGenres() {
        try {
            Map<String, Object> response = tmdbApiService.getTvGenres(DEFAULT_LANGUAGE);
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

    public Series getCachedSeriesById(Integer seriesId) {
        return seriesDao.findById(seriesId).orElse(null);
    }
}