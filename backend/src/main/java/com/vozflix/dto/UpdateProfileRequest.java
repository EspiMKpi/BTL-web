package com.vozflix.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UpdateProfileRequest {

    private String username;
    private String email;
    private String avatarUrl;
    private String currentPassword;
    private String newPassword;
}
