package com.vozflix.dao;

import com.vozflix.entity.Season;
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
public class SeasonDao {

    private final JdbcTemplate jdbcTemplate;

    private final RowMapper<Season> seasonRowMapper = (ResultSet rs, int rowNum) -> Season.builder()
            .seasonId(rs.getInt("season_id"))
            .seasonNumber(rs.getInt("season_number"))
            .seriesId(rs.getInt("series_id"))
            .name(rs.getString("name"))
            .overview(rs.getString("overview"))
            .posterPath(rs.getString("poster_path"))
            .airDate(rs.getDate("air_date") != null ? rs.getDate("air_date").toLocalDate() : null)
            .episodeCount(rs.getInt("episode_count"))
            .voteAverage(rs.getBigDecimal("vote_average"))
            .build();

    public int insert(Season season) {
        String sql = "INSERT INTO seasons (season_id, season_number, series_id, name, overview, poster_path, air_date, episode_count, vote_average) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)";
        return jdbcTemplate.update(sql, season.getSeasonId(), season.getSeasonNumber(), season.getSeriesId(),
                season.getName(), season.getOverview(), season.getPosterPath(), season.getAirDate(),
                season.getEpisodeCount(), season.getVoteAverage());
    }

    public int update(Season season) {
        String sql = "UPDATE seasons SET season_number=?, series_id=?, name=?, overview=?, poster_path=?, air_date=?, episode_count=?, vote_average=? WHERE season_id=?";
        return jdbcTemplate.update(sql, season.getSeasonNumber(), season.getSeriesId(), season.getName(),
                season.getOverview(), season.getPosterPath(), season.getAirDate(), season.getEpisodeCount(),
                season.getVoteAverage(), season.getSeasonId());
    }

    public int saveOrUpdate(Season season) {
        if (existsById(season.getSeasonId())) {
            return update(season);
        }
        return insert(season);
    }

    public Optional<Season> findById(Integer seasonId) {
        String sql = "SELECT * FROM seasons WHERE season_id = ?";
        List<Season> seasons = jdbcTemplate.query(sql, seasonRowMapper, seasonId);
        return seasons.isEmpty() ? Optional.empty() : Optional.of(seasons.get(0));
    }

    public Optional<Season> findBySeriesAndSeasonNumber(Integer seriesId, Integer seasonNumber) {
        String sql = "SELECT * FROM seasons WHERE series_id = ? AND season_number = ?";
        List<Season> seasons = jdbcTemplate.query(sql, seasonRowMapper, seriesId, seasonNumber);
        return seasons.isEmpty() ? Optional.empty() : Optional.of(seasons.get(0));
    }

    public List<Season> findBySeriesId(Integer seriesId) {
        String sql = "SELECT * FROM seasons WHERE series_id = ? ORDER BY season_number ASC";
        return jdbcTemplate.query(sql, seasonRowMapper, seriesId);
    }

    public boolean existsById(Integer seasonId) {
        String sql = "SELECT COUNT(*) FROM seasons WHERE season_id = ?";
        Integer count = jdbcTemplate.queryForObject(sql, Integer.class, seasonId);
        return count != null && count > 0;
    }

    public int deleteById(Integer seasonId) {
        String sql = "DELETE FROM seasons WHERE season_id = ?";
        return jdbcTemplate.update(sql, seasonId);
    }
}
