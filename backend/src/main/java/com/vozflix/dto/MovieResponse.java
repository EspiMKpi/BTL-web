package com.vozflix.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class MovieResponse {

    private Integer id;
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
    private Boolean adult;
    private Boolean video;
    private Integer runtime;
    private Long budget;
    private Long revenue;
    private String status;
    private String imdbId;
    private String homepage;
    private List<GenreDto> genres;
    private List<CountryDto> productionCountries;
    private List<LanguageDto> spokenLanguages;
    private CreditsResponse credits;
    private ImagesResponse images;

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class GenreDto {
        private Integer id;
        private String name;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class CountryDto {
        private String iso31661;
        private String name;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class LanguageDto {
        private String iso6391;
        private String englishName;
        private String name;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class CreditsResponse {
        private List<CastDto> cast;
        private List<CrewDto> crew;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class CastDto {
        private Integer castId;
        private String name;
        private String character;
        private String profilePath;
        private Integer order;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class CrewDto {
        private Integer id;
        private String name;
        private String department;
        private String job;
        private String profilePath;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class ImagesResponse {
        private List<ImageDto> backdrops;
        private List<ImageDto> posters;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @Builder
    public static class ImageDto {
        private String filePath;
        private Integer width;
        private Integer height;
        private Double aspectRatio;
        private Double voteAverage;
    }
}