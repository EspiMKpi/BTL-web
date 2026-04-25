package com.vozflix.api;

import retrofit2.http.GET;
import retrofit2.http.Path;
import retrofit2.http.Query;

import java.util.Map;

public interface TmdbApiService {

    @GET("movie/popular")
    Map<String, Object> getPopularMovies(
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("movie/top_rated")
    Map<String, Object> getTopRatedMovies(
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("movie/now_playing")
    Map<String, Object> getNowPlayingMovies(
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("movie/{movie_id}")
    Map<String, Object> getMovieDetails(
            @Path("movie_id") Integer movieId,
            @Query("language") String language
    );

    @GET("movie/{movie_id}/credits")
    Map<String, Object> getMovieCredits(
            @Path("movie_id") Integer movieId,
            @Query("language") String language
    );

    @GET("movie/{movie_id}/images")
    Map<String, Object> getMovieImages(
            @Path("movie_id") Integer movieId
    );

    @GET("tv/popular")
    Map<String, Object> getPopularTvShows(
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("tv/top_rated")
    Map<String, Object> getTopRatedTvShows(
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("tv/{tv_id}")
    Map<String, Object> getTvShowDetails(
            @Path("tv_id") Integer tvId,
            @Query("language") String language
    );

    @GET("tv/{tv_id}/season/{season_number}")
    Map<String, Object> getSeasonDetails(
            @Path("tv_id") Integer tvId,
            @Path("season_number") Integer seasonNumber,
            @Query("language") String language
    );

    @GET("tv/{tv_id}/credits")
    Map<String, Object> getTvShowCredits(
            @Path("tv_id") Integer tvId,
            @Query("language") String language
    );

    @GET("search/movie")
    Map<String, Object> searchMovies(
            @Query("query") String query,
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("search/tv")
    Map<String, Object> searchTvShows(
            @Query("query") String query,
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("search/multi")
    Map<String, Object> searchMulti(
            @Query("query") String query,
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("discover/movie")
    Map<String, Object> discoverMovies(
            @Query("page") Integer page,
            @Query("language") String language,
            @Query("sort_by") String sortBy,
            @Query("with_genres") String withGenres,
            @Query("primary_release_year") Integer primaryReleaseYear
    );

    @GET("discover/tv")
    Map<String, Object> discoverTvShows(
            @Query("page") Integer page,
            @Query("language") String language,
            @Query("sort_by") String sortBy,
            @Query("with_genres") String withGenres
    );

    @GET("genre/movie/list")
    Map<String, Object> getMovieGenres(
            @Query("language") String language
    );

    @GET("genre/tv/list")
    Map<String, Object> getTvGenres(
            @Query("language") String language
    );
}