package com.vozflix.dao;

import com.vozflix.entity.Series;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Optional;

@Slf4j
@Repository
@RequiredArgsConstructor
public class SeriesDao {

    private final JdbcTemplate jdbcTemplate;

    private final RowMapper<Series> seriesRowMapper = new RowMapper<Series>() {
        @Override
        public Series mapRow(ResultSet rs, int rowNum) throws SQLException {
            return Series.builder()
                    .seriesId(rs.getInt("series_id"))
                    .name(rs.getString("name"))
                    .originalName(rs.getString("original_name"))
                    .tagline(rs.getString("tagline"))
                    .overview(rs.getString("overview"))
                    .posterPath(rs.getString("poster_path"))
                    .backdropPath(rs.getString("backdrop_path"))
                    .firstAirDate(rs.getDate("first_air_date") != null ? rs.getDate("first_air_date").toLocalDate() : null)
                    .lastAirDate(rs.getDate("last_air_date") != null ? rs.getDate("last_air_date").toLocalDate() : null)
                    .originalLanguage(rs.getString("original_language"))
                    .popularity(rs.getBigDecimal("popularity"))
                    .voteAverage(rs.getBigDecimal("vote_average"))
                    .voteCount(rs.getInt("vote_count"))
                    .adult(rs.getBoolean("adult"))
                    .episodeRunTimeJson(rs.getString("episode_run_time_json"))
                    .type(rs.getString("type"))
                    .status(rs.getString("status"))
                    .imdbId(rs.getString("imdb_id"))
                    .homepage(rs.getString("homepage"))
                    .genresJson(rs.getString("genres_json"))
                    .networksJson(rs.getString("networks_json"))
                    .productionCountriesJson(rs.getString("production_countries_json"))
                    .spokenLanguagesJson(rs.getString("spoken_languages_json"))
                    .numberOfSeasons(rs.getInt("number_of_seasons"))
                    .numberOfEpisodes(rs.getInt("number_of_episodes"))
                    .build();
        }
    };

    public int insert(Series series) {
        String sql = "INSERT INTO series (series_id, name, original_name, tagline, overview, poster_path, backdrop_path, " +
                "first_air_date, last_air_date, original_language, popularity, vote_average, vote_count, " +
                "adult, episode_run_time_json, type, status, imdb_id, homepage, genres_json, " +
                "networks_json, production_countries_json, spoken_languages_json, " +
                "number_of_seasons, number_of_episodes) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
        return jdbcTemplate.update(sql, series.getSeriesId(), series.getName(), series.getOriginalName(), series.getTagline(),
                series.getOverview(), series.getPosterPath(), series.getBackdropPath(), series.getFirstAirDate(),
                series.getLastAirDate(), series.getOriginalLanguage(), series.getPopularity(), series.getVoteAverage(), series.getVoteCount(),
                series.getAdult(), series.getEpisodeRunTimeJson(), series.getType(), series.getStatus(), series.getImdbId(),
                series.getHomepage(), series.getGenresJson(), series.getNetworksJson(), series.getProductionCountriesJson(),
                series.getSpokenLanguagesJson(), series.getNumberOfSeasons(), series.getNumberOfEpisodes());
    }

        public int update(Series series) {
        String sql = "UPDATE series SET name = ?, original_name = ?, tagline = ?, overview = ?, poster_path = ?, backdrop_path = ?, " +
            "first_air_date = ?, last_air_date = ?, original_language = ?, popularity = ?, vote_average = ?, vote_count = ?, " +
            "adult = ?, episode_run_time_json = ?, type = ?, status = ?, imdb_id = ?, homepage = ?, genres_json = ?, " +
            "networks_json = ?, production_countries_json = ?, spoken_languages_json = ?, number_of_seasons = ?, number_of_episodes = ? " +
            "WHERE series_id = ?";
        return jdbcTemplate.update(sql, series.getName(), series.getOriginalName(), series.getTagline(), series.getOverview(),
            series.getPosterPath(), series.getBackdropPath(), series.getFirstAirDate(), series.getLastAirDate(),
            series.getOriginalLanguage(), series.getPopularity(), series.getVoteAverage(), series.getVoteCount(),
            series.getAdult(), series.getEpisodeRunTimeJson(), series.getType(), series.getStatus(), series.getImdbId(),
            series.getHomepage(), series.getGenresJson(), series.getNetworksJson(), series.getProductionCountriesJson(),
            series.getSpokenLanguagesJson(), series.getNumberOfSeasons(), series.getNumberOfEpisodes(), series.getSeriesId());
        }

    public int saveOrUpdate(Series series) {
        if (existsById(series.getSeriesId())) {
            return update(series);
        }

        return insert(series);
    }

    public Optional<Series> findById(Integer seriesId) {
        String sql = "SELECT * FROM series WHERE series_id = ?";
        List<Series> seriesList = jdbcTemplate.query(sql, seriesRowMapper, seriesId);
        return seriesList.isEmpty() ? Optional.empty() : Optional.of(seriesList.get(0));
    }

    public boolean existsById(Integer seriesId) {
        String sql = "SELECT COUNT(*) FROM series WHERE series_id = ?";
        Integer count = jdbcTemplate.queryForObject(sql, Integer.class, seriesId);
        return count != null && count > 0;
    }

    public List<Series> findAll(int limit, int offset) {
        String sql = "SELECT * FROM series ORDER BY popularity DESC LIMIT ? OFFSET ?";
        return jdbcTemplate.query(sql, seriesRowMapper, limit, offset);
    }

    public int count() {
        String sql = "SELECT COUNT(*) FROM series";
        return jdbcTemplate.queryForObject(sql, Integer.class);
    }

    public List<Series> findByNameContaining(String name, int limit, int offset) {
        String sql = "SELECT * FROM series WHERE LOWER(name) LIKE LOWER(CONCAT('%', ?, '%')) ORDER BY popularity DESC LIMIT ? OFFSET ?";
        return jdbcTemplate.query(sql, seriesRowMapper, name, limit, offset);
    }

    public List<Series> findTopRated(int limit, int offset) {
        String sql = "SELECT * FROM series ORDER BY vote_average DESC LIMIT ? OFFSET ?";
        return jdbcTemplate.query(sql, seriesRowMapper, limit, offset);
    }

    public int deleteById(Integer seriesId) {
        String sql = "DELETE FROM series WHERE series_id = ?";
        return jdbcTemplate.update(sql, seriesId);
    }
}