package com.vozflix.controller;

import com.vozflix.dao.UserDao;
import com.vozflix.dto.AuthResponse;
import com.vozflix.dto.LoginRequest;
import com.vozflix.dto.RegisterRequest;
import com.vozflix.dto.UpdateProfileRequest;
import com.vozflix.entity.User;
import com.vozflix.security.JwtUtil;
import com.vozflix.security.RequireRole;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.beans.factory.annotation.Value;
import jakarta.servlet.http.HttpServletRequest;
import java.util.concurrent.TimeUnit;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final UserDao userDao;
    private final JwtUtil jwtUtil;
    private final StringRedisTemplate redisTemplate;

    @Value("${jwt.expiration:86400000}")
    private long expiration;

    @PostMapping("/register")
    public ResponseEntity<?> register(@RequestBody RegisterRequest request) {
        log.info("Register request for: {}", request.getEmail());

        // Check if email exists
        if (userDao.existsByEmail(request.getEmail())) {
            return ResponseEntity.badRequest()
                    .body(Map.of("error", "Email already exists"));
        }

        // Check if username exists
        if (userDao.existsByUsername(request.getUsername())) {
            return ResponseEntity.badRequest()
                    .body(Map.of("error", "Username already exists"));
        }

        // Hash password
        String hashedPassword = hashPassword(request.getPassword());

        // Create user with default role
        User user = User.builder()
                .username(request.getUsername())
                .email(request.getEmail())
                .passwordHash(hashedPassword)
                .role(User.UserRole.user)
                .isActive(true)
                .build();

        userDao.insert(user);

        // Generate token
        User savedUser = userDao.findByEmail(request.getEmail()).orElse(null);
        String token = jwtUtil.generateToken(
                savedUser.getUserId(),
                savedUser.getUsername(),
                savedUser.getRole().name()
        );

        // Store token in Redis
        redisTemplate.opsForValue().set("auth:token:" + token, String.valueOf(savedUser.getUserId()), expiration, TimeUnit.MILLISECONDS);

        log.info("User registered successfully: {}", request.getEmail());

        return ResponseEntity.ok(AuthResponse.builder()
                .userId(savedUser.getUserId())
                .username(savedUser.getUsername())
                .email(savedUser.getEmail())
            .avatarUrl(savedUser.getAvatarUrl())
                .role(savedUser.getRole().name())
                .token(token)
                .build());
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody LoginRequest request) {
        log.info("Login attempt for: {}", request.getEmail());

        // Find user by email
        User user = userDao.findByEmail(request.getEmail()).orElse(null);

        if (user == null) {
            return ResponseEntity.status(401)
                    .body(Map.of("error", "Invalid credentials"));
        }

        // Verify password
        String hashedInput = hashPassword(request.getPassword());
        if (!hashedInput.equals(user.getPasswordHash())) {
            return ResponseEntity.status(401)
                    .body(Map.of("error", "Invalid credentials"));
        }

        // Check if user is active
        if (!user.getIsActive()) {
            return ResponseEntity.status(403)
                    .body(Map.of("error", "Account is disabled"));
        }

        String token = jwtUtil.generateToken(
                user.getUserId(),
                user.getUsername(),
                user.getRole().name()
        );

        // Store token in Redis
        redisTemplate.opsForValue().set("auth:token:" + token, String.valueOf(user.getUserId()), expiration, TimeUnit.MILLISECONDS);

        log.info("User logged in successfully: {}", request.getEmail());

        return ResponseEntity.ok(AuthResponse.builder()
                .userId(user.getUserId())
                .username(user.getUsername())
                .email(user.getEmail())
            .avatarUrl(user.getAvatarUrl())
                .role(user.getRole().name())
                .token(token)
                .build());
    }

    @PutMapping("/profile")
    @RequireRole({"user", "admin", "curator"})
    public ResponseEntity<?> updateProfile(
            @RequestBody UpdateProfileRequest request,
            HttpServletRequest httpRequest) {
        Integer userId = (Integer) httpRequest.getAttribute("userId");
        if (userId == null) {
            return ResponseEntity.status(401).body(Map.of("error", "Unauthorized"));
        }

        User user = userDao.findById(userId).orElse(null);
        if (user == null) {
            return ResponseEntity.status(404).body(Map.of("error", "User not found"));
        }

        String username = trimOrNull(request.getUsername());
        String email = trimOrNull(request.getEmail());
        String avatarUrl = trimOrNull(request.getAvatarUrl());

        if (isBlank(username)) {
            username = user.getUsername();
        }
        if (isBlank(email)) {
            email = user.getEmail();
        }

        if (!username.equals(user.getUsername()) && userDao.existsByUsername(username)) {
            return ResponseEntity.badRequest().body(Map.of("error", "Username already exists"));
        }
        if (!email.equals(user.getEmail()) && userDao.existsByEmail(email)) {
            return ResponseEntity.badRequest().body(Map.of("error", "Email already exists"));
        }

        String newPassword = trimOrNull(request.getNewPassword());
        if (!isBlank(newPassword)) {
            String currentPassword = trimOrNull(request.getCurrentPassword());
            if (isBlank(currentPassword)) {
                return ResponseEntity.badRequest().body(Map.of("error", "Current password is required"));
            }
            String hashedInput = hashPassword(currentPassword);
            if (!hashedInput.equals(user.getPasswordHash())) {
                return ResponseEntity.status(401).body(Map.of("error", "Invalid current password"));
            }
            user.setPasswordHash(hashPassword(newPassword));
        }

        user.setUsername(username);
        user.setEmail(email);
        if (!isBlank(avatarUrl)) {
            user.setAvatarUrl(avatarUrl);
        }

        userDao.update(user);

        String authHeader = httpRequest.getHeader("Authorization");
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            String oldToken = authHeader.substring(7);
            redisTemplate.delete("auth:token:" + oldToken);
        }

        String token = jwtUtil.generateToken(
                user.getUserId(),
                user.getUsername(),
                user.getRole().name()
        );

        redisTemplate.opsForValue().set(
                "auth:token:" + token,
                String.valueOf(user.getUserId()),
                expiration,
                TimeUnit.MILLISECONDS
        );

        return ResponseEntity.ok(AuthResponse.builder()
                .userId(user.getUserId())
                .username(user.getUsername())
                .email(user.getEmail())
                .avatarUrl(user.getAvatarUrl())
                .role(user.getRole().name())
                .token(token)
                .build());
    }

    @PostMapping("/logout")
    public ResponseEntity<?> logout(HttpServletRequest request) {
        String authHeader = request.getHeader("Authorization");
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            String token = authHeader.substring(7);
            redisTemplate.delete("auth:token:" + token);
            log.info("User logged out successfully, token invalidated");
        }
        return ResponseEntity.ok().body(Map.of("message", "Logged out successfully"));
    }

    private String hashPassword(String password) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(password.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("Failed to hash password", e);
        }
    }

    private boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }

    private String trimOrNull(String value) {
        if (value == null) return null;
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}