package com.vozflix.entity;

import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Series {

    private Integer seriesId;
    private String name;
    private String originalName;
    private String tagline;
    private String overview;
    private String posterPath;
    private String backdropPath;
    private LocalDate firstAirDate;
    private LocalDate lastAirDate;
    private String originalLanguage;
    private BigDecimal popularity;
    private BigDecimal voteAverage;
    private Integer voteCount;
    @Builder.Default
    private Boolean adult = false;
    private String episodeRunTimeJson;
    private String type;
    private String status;
    private String imdbId;
    private String homepage;
    private String genresJson;
    private String networksJson;
    private String productionCountriesJson;
    private String spokenLanguagesJson;
    private Integer numberOfSeasons;
    private Integer numberOfEpisodes;
}