package com.vozflix.dao;

import com.vozflix.entity.WatchlistItem;
import com.vozflix.entity.WatchlistItem.ContentType;
import com.vozflix.entity.WatchlistItem.WatchlistStatus;
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
public class WatchlistDao {

    private final JdbcTemplate jdbcTemplate;

    private final RowMapper<WatchlistItem> watchlistRowMapper = (ResultSet rs, int rowNum) -> WatchlistItem.builder()
            .watchlistId(rs.getInt("watchlist_id"))
            .userId(rs.getInt("user_id"))
            .contentType(ContentType.valueOf(rs.getString("content_type")))
            .tmdbId(rs.getInt("tmdb_id"))
            .status(WatchlistStatus.valueOf(rs.getString("status")))
            .progressSeconds(rs.getInt("progress_seconds"))
            .currentEpisode(rs.getInt("current_episode"))
            .currentSeason(rs.getInt("current_season"))
            .rating(rs.getBigDecimal("rating"))
            .review(rs.getString("review"))
            .isBookmarked(rs.getBoolean("is_bookmarked"))
            .build();

    public int insert(WatchlistItem item) {
        String sql = """
            INSERT INTO watchlist_items (user_id, content_type, tmdb_id, status, progress_seconds,
                                      current_episode, current_season, rating, review, is_bookmarked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """;
        return jdbcTemplate.update(sql,
                item.getUserId(),
                item.getContentType().name(),
                item.getTmdbId(),
                item.getStatus().name(),
                item.getProgressSeconds(),
                item.getCurrentEpisode(),
                item.getCurrentSeason(),
                item.getRating(),
                item.getReview(),
                item.getIsBookmarked()
        );
    }

    public int update(WatchlistItem item) {
        String sql = """
            UPDATE watchlist_items SET status=?, progress_seconds=?, current_episode=?, current_season=?,
                                  rating=?, review=?, is_bookmarked=?
            WHERE watchlist_id=?
            """;
        return jdbcTemplate.update(sql,
                item.getStatus().name(),
                item.getProgressSeconds(),
                item.getCurrentEpisode(),
                item.getCurrentSeason(),
                item.getRating(),
                item.getReview(),
                item.getIsBookmarked(),
                item.getWatchlistId()
        );
    }

    public Optional<WatchlistItem> findById(Integer watchlistId) {
        String sql = "SELECT * FROM watchlist_items WHERE watchlist_id = ?";
        List<WatchlistItem> items = jdbcTemplate.query(sql, watchlistRowMapper, watchlistId);
        return items.isEmpty() ? Optional.empty() : Optional.of(items.get(0));
    }

    public List<WatchlistItem> findByUserId(Integer userId) {
        String sql = "SELECT * FROM watchlist_items WHERE user_id = ? ORDER BY updated_at DESC";
        return jdbcTemplate.query(sql, watchlistRowMapper, userId);
    }

    public List<WatchlistItem> findByUserIdAndStatus(Integer userId, WatchlistStatus status) {
        String sql = "SELECT * FROM watchlist_items WHERE user_id = ? AND status = ? ORDER BY updated_at DESC";
        return jdbcTemplate.query(sql, watchlistRowMapper, userId, status.name());
    }

    public Optional<WatchlistItem> findByUserIdAndTmdbIdAndContentType(Integer userId, Integer tmdbId, ContentType contentType) {
        String sql = "SELECT * FROM watchlist_items WHERE user_id = ? AND tmdb_id = ? AND content_type = ?";
        List<WatchlistItem> items = jdbcTemplate.query(sql, watchlistRowMapper, userId, tmdbId, contentType.name());
        return items.isEmpty() ? Optional.empty() : Optional.of(items.get(0));
    }

    public boolean existsByUserIdAndTmdbIdAndContentType(Integer userId, Integer tmdbId, ContentType contentType) {
        String sql = "SELECT COUNT(*) FROM watchlist_items WHERE user_id = ? AND tmdb_id = ? AND content_type = ?";
        Integer count = jdbcTemplate.queryForObject(sql, Integer.class, userId, tmdbId, contentType.name());
        return count != null && count > 0;
    }

    public int deleteById(Integer watchlistId) {
        String sql = "DELETE FROM watchlist_items WHERE watchlist_id = ?";
        return jdbcTemplate.update(sql, watchlistId);
    }

    public int deleteByUserIdAndTmdbIdAndContentType(Integer userId, Integer tmdbId, ContentType contentType) {
        String sql = "DELETE FROM watchlist_items WHERE user_id = ? AND tmdb_id = ? AND content_type = ?";
        return jdbcTemplate.update(sql, userId, tmdbId, contentType.name());
    }

    public int countByUserId(Integer userId) {
        String sql = "SELECT COUNT(*) FROM watchlist_items WHERE user_id = ?";
        return jdbcTemplate.queryForObject(sql, Integer.class, userId);
    }
}