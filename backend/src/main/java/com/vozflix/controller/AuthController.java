package com.vozflix.controller;

import com.vozflix.dao.UserDao;
import com.vozflix.dto.AuthResponse;
import com.vozflix.dto.LoginRequest;
import com.vozflix.dto.RegisterRequest;
import com.vozflix.entity.User;
import com.vozflix.security.JwtUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

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

        log.info("User registered successfully: {}", request.getEmail());

        return ResponseEntity.ok(AuthResponse.builder()
                .userId(savedUser.getUserId())
                .username(savedUser.getUsername())
                .email(savedUser.getEmail())
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

        // Generate token
        String token = jwtUtil.generateToken(
                user.getUserId(),
                user.getUsername(),
                user.getRole().name()
        );

        log.info("User logged in successfully: {}", request.getEmail());

        return ResponseEntity.ok(AuthResponse.builder()
                .userId(user.getUserId())
                .username(user.getUsername())
                .email(user.getEmail())
                .role(user.getRole().name())
                .token(token)
                .build());
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
}