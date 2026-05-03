package com.vozflix.api;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Path;
import retrofit2.http.Query;

import java.util.Map;

public interface TmdbApiService {

    @GET("movie/popular")
    Call<Map<String, Object>> getPopularMovies(
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("movie/top_rated")
    Call<Map<String, Object>> getTopRatedMovies(
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("movie/now_playing")
    Call<Map<String, Object>> getNowPlayingMovies(
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("movie/{movie_id}")
    Call<Map<String, Object>> getMovieDetails(
            @Path("movie_id") Integer movieId,
            @Query("language") String language
    );

    @GET("movie/{movie_id}/credits")
    Call<Map<String, Object>> getMovieCredits(
            @Path("movie_id") Integer movieId,
            @Query("language") String language
    );

    @GET("movie/{movie_id}/images")
    Call<Map<String, Object>> getMovieImages(
            @Path("movie_id") Integer movieId
    );

    @GET("tv/popular")
    Call<Map<String, Object>> getPopularTvShows(
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("tv/top_rated")
    Call<Map<String, Object>> getTopRatedTvShows(
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("tv/{tv_id}")
    Call<Map<String, Object>> getTvShowDetails(
            @Path("tv_id") Integer tvId,
            @Query("language") String language
    );

    @GET("tv/{tv_id}/season/{season_number}")
    Call<Map<String, Object>> getSeasonDetails(
            @Path("tv_id") Integer tvId,
            @Path("season_number") Integer seasonNumber,
            @Query("language") String language
    );

    @GET("tv/{tv_id}/credits")
    Call<Map<String, Object>> getTvShowCredits(
            @Path("tv_id") Integer tvId,
            @Query("language") String language
    );

    @GET("search/movie")
    Call<Map<String, Object>> searchMovies(
            @Query("query") String query,
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("search/tv")
    Call<Map<String, Object>> searchTvShows(
            @Query("query") String query,
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("search/multi")
    Call<Map<String, Object>> searchMulti(
            @Query("query") String query,
            @Query("page") Integer page,
            @Query("language") String language
    );

    @GET("discover/movie")
    Call<Map<String, Object>> discoverMovies(
            @Query("page") Integer page,
            @Query("language") String language,
            @Query("sort_by") String sortBy,
            @Query("with_genres") String withGenres,
            @Query("primary_release_year") Integer primaryReleaseYear
    );

    @GET("discover/tv")
    Call<Map<String, Object>> discoverTvShows(
            @Query("page") Integer page,
            @Query("language") String language,
            @Query("sort_by") String sortBy,
            @Query("with_genres") String withGenres
    );

    @GET("genre/movie/list")
    Call<Map<String, Object>> getMovieGenres(
            @Query("language") String language
    );

    @GET("genre/tv/list")
    Call<Map<String, Object>> getTvGenres(
            @Query("language") String language
    );
}
