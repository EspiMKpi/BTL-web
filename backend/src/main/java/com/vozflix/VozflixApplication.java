package com.vozflix;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;

@SpringBootApplication
@EnableCaching
public class VozflixApplication {

    public static void main(String[] args) {
        SpringApplication.run(VozflixApplication.class, args);
    }
}