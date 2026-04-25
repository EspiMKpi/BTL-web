package com.vozflix.dao;

import com.vozflix.entity.Genre;
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
public class GenreDao {

    private final JdbcTemplate jdbcTemplate;

    private final RowMapper<Genre> genreRowMapper = (ResultSet rs, int rowNum) -> Genre.builder()
            .genreId(rs.getInt("genre_id"))
            .name(rs.getString("name"))
            .build();

    public int insert(Genre genre) {
        String sql = "INSERT INTO genres (genre_id, name) VALUES (?, ?)";
        return jdbcTemplate.update(sql, genre.getGenreId(), genre.getName());
    }

    public int insertBatch(List<Genre> genres) {
        int count = 0;
        for (Genre genre : genres) {
            insert(genre);
            count++;
        }
        return count;
    }

    public Optional<Genre> findById(Integer genreId) {
        String sql = "SELECT * FROM genres WHERE genre_id = ?";
        List<Genre> genres = jdbcTemplate.query(sql, genreRowMapper, genreId);
        return genres.isEmpty() ? Optional.empty() : Optional.of(genres.get(0));
    }

    public Optional<Genre> findByName(String name) {
        String sql = "SELECT * FROM genres WHERE name = ?";
        List<Genre> genres = jdbcTemplate.query(sql, genreRowMapper, name);
        return genres.isEmpty() ? Optional.empty() : Optional.of(genres.get(0));
    }

    public List<Genre> findAll() {
        String sql = "SELECT * FROM genres ORDER BY name ASC";
        return jdbcTemplate.query(sql, genreRowMapper);
    }

    public boolean existsByName(String name) {
        String sql = "SELECT COUNT(*) FROM genres WHERE name = ?";
        Integer count = jdbcTemplate.queryForObject(sql, Integer.class, name);
        return count != null && count > 0;
    }

    public int deleteAll() {
        String sql = "DELETE FROM genres";
        return jdbcTemplate.update(sql);
    }
}