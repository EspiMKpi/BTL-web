package com.vozflix.dao;

import com.vozflix.entity.Movie;
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
public class MovieDao {

    private final JdbcTemplate jdbcTemplate;

    private final RowMapper<Movie> movieRowMapper = new RowMapper<Movie>() {
        @Override
        public Movie mapRow(ResultSet rs, int rowNum) throws SQLException {
            return Movie.builder()
                    .movieId(rs.getInt("movie_id"))
                    .title(rs.getString("title"))
                    .originalTitle(rs.getString("original_title"))
                    .tagline(rs.getString("tagline"))
                    .overview(rs.getString("overview"))
                    .posterPath(rs.getString("poster_path"))
                    .backdropPath(rs.getString("backdrop_path"))
                    .releaseDate(rs.getDate("release_date") != null ? rs.getDate("release_date").toLocalDate() : null)
                    .originalLanguage(rs.getString("original_language"))
                    .popularity(rs.getBigDecimal("popularity"))
                    .voteAverage(rs.getBigDecimal("vote_average"))
                    .voteCount(rs.getInt("vote_count"))
                    .adult(rs.getBoolean("adult"))
                    .video(rs.getBoolean("video"))
                    .runtime(rs.getInt("runtime"))
                    .budget(rs.getLong("budget"))
                    .revenue(rs.getLong("revenue"))
                    .status(rs.getString("status"))
                    .imdbId(rs.getString("imdb_id"))
                    .homepage(rs.getString("homepage"))
                    .genresJson(rs.getString("genres_json"))
                    .productionCountriesJson(rs.getString("production_countries_json"))
                    .spokenLanguagesJson(rs.getString("spoken_languages_json"))
                    .build();
        }
    };

    public int insert(Movie movie) {
        String sql = "INSERT INTO movies (movie_id, title, original_title, tagline, overview, poster_path, backdrop_path, " +
                "release_date, original_language, popularity, vote_average, vote_count, adult, video, " +
                "runtime, budget, revenue, status, imdb_id, homepage, genres_json, " +
                "production_countries_json, spoken_languages_json) " +
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
        return jdbcTemplate.update(sql, movie.getMovieId(), movie.getTitle(), movie.getOriginalTitle(), movie.getTagline(),
                movie.getOverview(), movie.getPosterPath(), movie.getBackdropPath(), movie.getReleaseDate(),
                movie.getOriginalLanguage(), movie.getPopularity(), movie.getVoteAverage(), movie.getVoteCount(),
                movie.getAdult(), movie.getVideo(), movie.getRuntime(), movie.getBudget(), movie.getRevenue(),
                movie.getStatus(), movie.getImdbId(), movie.getHomepage(), movie.getGenresJson(),
                movie.getProductionCountriesJson(), movie.getSpokenLanguagesJson());
    }

    public int saveOrUpdate(Movie movie) {
        if (existsById(movie.getMovieId())) {
            return update(movie);
        }

        return insert(movie);
    }

    public int update(Movie movie) {
        String sql = "UPDATE movies SET title=?, original_title=?, tagline=?, overview=?, poster_path=?, backdrop_path=?, " +
                "release_date=?, original_language=?, popularity=?, vote_average=?, vote_count=?, adult=?, video=?, " +
                "runtime=?, budget=?, revenue=?, status=?, imdb_id=?, homepage=?, genres_json=?, " +
                "production_countries_json=?, spoken_languages_json=? WHERE movie_id=?";
        return jdbcTemplate.update(sql, movie.getTitle(), movie.getOriginalTitle(), movie.getTagline(),
                movie.getOverview(), movie.getPosterPath(), movie.getBackdropPath(), movie.getReleaseDate(),
                movie.getOriginalLanguage(), movie.getPopularity(), movie.getVoteAverage(), movie.getVoteCount(),
                movie.getAdult(), movie.getVideo(), movie.getRuntime(), movie.getBudget(), movie.getRevenue(),
                movie.getStatus(), movie.getImdbId(), movie.getHomepage(), movie.getGenresJson(),
                movie.getProductionCountriesJson(), movie.getSpokenLanguagesJson(), movie.getMovieId());
    }

    public Optional<Movie> findById(Integer movieId) {
        String sql = "SELECT * FROM movies WHERE movie_id = ?";
        List<Movie> movies = jdbcTemplate.query(sql, movieRowMapper, movieId);
        return movies.isEmpty() ? Optional.empty() : Optional.of(movies.get(0));
    }

    public boolean existsById(Integer movieId) {
        String sql = "SELECT COUNT(*) FROM movies WHERE movie_id = ?";
        Integer count = jdbcTemplate.queryForObject(sql, Integer.class, movieId);
        return count != null && count > 0;
    }

    public List<Movie> findAll(int limit, int offset) {
        String sql = "SELECT * FROM movies ORDER BY popularity DESC LIMIT ? OFFSET ?";
        return jdbcTemplate.query(sql, movieRowMapper, limit, offset);
    }

    public List<Movie> findByTitleContaining(String title, int limit, int offset) {
        String sql = "SELECT * FROM movies WHERE LOWER(title) LIKE LOWER(CONCAT('%', ?, '%')) ORDER BY popularity DESC LIMIT ? OFFSET ?";
        return jdbcTemplate.query(sql, movieRowMapper, title, limit, offset);
    }

    public List<Movie> findTopRated(int limit, int offset) {
        String sql = "SELECT * FROM movies ORDER BY vote_average DESC LIMIT ? OFFSET ?";
        return jdbcTemplate.query(sql, movieRowMapper, limit, offset);
    }

    public int count() {
        String sql = "SELECT COUNT(*) FROM movies";
        return jdbcTemplate.queryForObject(sql, Integer.class);
    }

    public int deleteById(Integer movieId) {
        String sql = "DELETE FROM movies WHERE movie_id = ?";
        return jdbcTemplate.update(sql, movieId);
    }
}