package com.vozflix.entity;

import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Season {

    private Integer seasonId;
    private Integer seasonNumber;
    private Integer seriesId;
    private String name;
    private String overview;
    private String posterPath;
    private LocalDate airDate;
    private Integer episodeCount;
    private BigDecimal voteAverage;
}