package com.vozflix.entity;

import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Episode {

    private Integer episodeId;
    private Integer episodeNumber;
    private Integer seasonNumber;
    private Integer seriesId;
    private String name;
    private String overview;
    private String stillPath;
    private LocalDate airDate;
    private Integer runtime;
    private BigDecimal voteAverage;
    private Integer voteCount;
}