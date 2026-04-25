package com.vozflix.entity;

import lombok.*;

import java.math.BigDecimal;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class WatchlistItem {

    private Integer watchlistId;
    private Integer userId;
    private ContentType contentType;
    private Integer tmdbId;
    private WatchlistStatus status;
    @Builder.Default
    private Integer progressSeconds = 0;
    @Builder.Default
    private Integer currentEpisode = 1;
    @Builder.Default
    private Integer currentSeason = 1;
    private BigDecimal rating;
    private String review;
    @Builder.Default
    private Boolean isBookmarked = false;

    public enum ContentType {
        movie, series
    }

    public enum WatchlistStatus {
        CONTINUE, WISHLIST, COMPLETED, FAVORITES
    }
}