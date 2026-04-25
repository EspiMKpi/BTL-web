package com.vozflix.controller;

import com.vozflix.security.RequireRole;
import com.vozflix.service.SessionService;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/session")
@RequiredArgsConstructor
public class SessionController {

    private final SessionService sessionService;

    @GetMapping("/theme")
    public ResponseEntity<?> getTheme(HttpServletRequest request) {
        Integer userId = (Integer) request.getAttribute("userId");
        if (userId == null) {
            return ResponseEntity.ok(Map.of("theme", "light"));
        }
        String theme = sessionService.getTheme(userId);
        return ResponseEntity.ok(Map.of("theme", theme));
    }

    @PutMapping("/theme")
    @RequireRole({"user", "admin", "curator"})
    public ResponseEntity<?> setTheme(
            @RequestBody Map<String, String> body,
            HttpServletRequest request) {
        Integer userId = (Integer) request.getAttribute("userId");
        String theme = body.get("theme");

        if (theme == null || (!theme.equals("light") && !theme.equals("dark"))) {
            return ResponseEntity.badRequest().body(Map.of("error", "Invalid theme. Use 'light' or 'dark'"));
        }

        sessionService.saveTheme(userId, theme);
        return ResponseEntity.ok(Map.of("theme", theme));
    }
}