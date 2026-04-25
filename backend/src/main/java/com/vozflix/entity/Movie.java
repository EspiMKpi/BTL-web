package com.vozflix.entity;

import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Movie {

    private Integer movieId;
    private String title;
    private String originalTitle;
    private String tagline;
    private String overview;
    private String posterPath;
    private String backdropPath;
    private LocalDate releaseDate;
    private String originalLanguage;
    private BigDecimal popularity;
    private BigDecimal voteAverage;
    private Integer voteCount;
    @Builder.Default
    private Boolean adult = false;
    @Builder.Default
    private Boolean video = false;
    private Integer runtime;
    private Long budget;
    private Long revenue;
    private String status;
    private String imdbId;
    private String homepage;
    private String genresJson;
    private String productionCountriesJson;
    private String spokenLanguagesJson;
}