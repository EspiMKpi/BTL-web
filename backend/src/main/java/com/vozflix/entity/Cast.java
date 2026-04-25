package com.vozflix.entity;

import lombok.*;

import java.math.BigDecimal;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Cast {

    private Integer castId;
    private Integer movieId;
    private String creditId;
    private String name;
    private String originalName;
    private String characterName;
    private String department;
    private String job;
    private Integer gender;
    private String profilePath;
    private BigDecimal popularity;
    private Integer ordering;
}