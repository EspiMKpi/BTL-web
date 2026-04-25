package com.vozflix.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Data
@Configuration
@ConfigurationProperties(prefix = "tmdb.api")
public class TmdbConfig {

    private String key;
    private String baseUrl;
    private String imageBaseUrl;
}