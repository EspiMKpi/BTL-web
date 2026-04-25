package com.vozflix.entity;

import lombok.*;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Genre {

    private Integer genreId;
    private String name;
}