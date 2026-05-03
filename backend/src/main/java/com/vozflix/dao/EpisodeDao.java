package com.vozflix.dao;

import com.vozflix.entity.Episode;
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
public class EpisodeDao {

    private final JdbcTemplate jdbcTemplate;

    private final RowMapper<Episode> episodeRowMapper = (ResultSet rs, int rowNum) -> Episode.builder()
            .episodeId(rs.getInt("episode_id"))
            .episodeNumber(rs.getInt("episode_number"))
            .seasonNumber(rs.getInt("season_number"))
            .seriesId(rs.getInt("series_id"))
            .name(rs.getString("name"))
            .overview(rs.getString("overview"))
            .stillPath(rs.getString("still_path"))
            .airDate(rs.getDate("air_date") != null ? rs.getDate("air_date").toLocalDate() : null)
            .runtime(rs.getInt("runtime"))
            .voteAverage(rs.getBigDecimal("vote_average"))
            .voteCount(rs.getInt("vote_count"))
            .build();

    public int insert(Episode episode) {
        String sql = "INSERT INTO episodes (episode_id, episode_number, season_number, series_id, name, overview, still_path, air_date, runtime, vote_average, vote_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
        return jdbcTemplate.update(sql, episode.getEpisodeId(), episode.getEpisodeNumber(), episode.getSeasonNumber(),
                episode.getSeriesId(), episode.getName(), episode.getOverview(), episode.getStillPath(),
                episode.getAirDate(), episode.getRuntime(), episode.getVoteAverage(), episode.getVoteCount());
    }

    public int update(Episode episode) {
        String sql = "UPDATE episodes SET episode_number=?, season_number=?, series_id=?, name=?, overview=?, still_path=?, air_date=?, runtime=?, vote_average=?, vote_count=? WHERE episode_id=?";
        return jdbcTemplate.update(sql, episode.getEpisodeNumber(), episode.getSeasonNumber(), episode.getSeriesId(),
                episode.getName(), episode.getOverview(), episode.getStillPath(), episode.getAirDate(),
                episode.getRuntime(), episode.getVoteAverage(), episode.getVoteCount(), episode.getEpisodeId());
    }

    public int saveOrUpdate(Episode episode) {
        if (existsById(episode.getEpisodeId())) {
            return update(episode);
        }
        return insert(episode);
    }

    public Optional<Episode> findById(Integer episodeId) {
        String sql = "SELECT * FROM episodes WHERE episode_id = ?";
        List<Episode> episodes = jdbcTemplate.query(sql, episodeRowMapper, episodeId);
        return episodes.isEmpty() ? Optional.empty() : Optional.of(episodes.get(0));
    }

    public List<Episode> findBySeason(Integer seriesId, Integer seasonNumber) {
        String sql = "SELECT * FROM episodes WHERE series_id = ? AND season_number = ? ORDER BY episode_number ASC";
        return jdbcTemplate.query(sql, episodeRowMapper, seriesId, seasonNumber);
    }

    public boolean existsById(Integer episodeId) {
        String sql = "SELECT COUNT(*) FROM episodes WHERE episode_id = ?";
        Integer count = jdbcTemplate.queryForObject(sql, Integer.class, episodeId);
        return count != null && count > 0;
    }

    public int deleteById(Integer episodeId) {
        String sql = "DELETE FROM episodes WHERE episode_id = ?";
        return jdbcTemplate.update(sql, episodeId);
    }
}
