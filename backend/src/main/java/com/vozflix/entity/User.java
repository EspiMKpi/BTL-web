package com.vozflix.entity;

import lombok.*;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User {

    private Integer userId;
    private String username;
    private String email;
    private String passwordHash;
    private String avatarUrl;
    @Builder.Default
    private UserRole role = UserRole.user;
    @Builder.Default
    private Boolean isActive = true;

    public enum UserRole {
        user, admin, curator
    }
}