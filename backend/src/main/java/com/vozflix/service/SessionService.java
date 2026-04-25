package com.vozflix.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class SessionService {

    private final RedisTemplate<String, Object> redisTemplate;

    @Value("${session.ttl:86400}")
    private long sessionTtlSeconds;

    private static final String SESSION_PREFIX = "session:";

    public void saveTheme(Integer userId, String theme) {
        try {
            String key = SESSION_PREFIX + userId;
            Map<String, Object> session = new HashMap<>();
            session.put("theme", theme);
            session.put("userId", userId);
            redisTemplate.opsForHash().putAll(key, session);
            redisTemplate.expire(key, sessionTtlSeconds, TimeUnit.SECONDS);
            log.debug("Theme saved for user {}: {}", userId, theme);
        } catch (Exception e) {
            log.error("Failed to save theme for user {}: {}", userId, e.getMessage());
        }
    }

    public String getTheme(Integer userId) {
        try {
            String key = SESSION_PREFIX + userId;
            Object theme = redisTemplate.opsForHash().get(key, "theme");
            return theme != null ? theme.toString() : "light";
        } catch (Exception e) {
            log.error("Failed to get theme for user {}: {}", userId, e.getMessage());
            return "light";
        }
    }

    public void saveSession(Integer userId, Map<String, Object> sessionData) {
        try {
            String key = SESSION_PREFIX + userId;
            redisTemplate.opsForHash().putAll(key, sessionData);
            redisTemplate.expire(key, sessionTtlSeconds, TimeUnit.SECONDS);
            log.debug("Session saved for user {}", userId);
        } catch (Exception e) {
            log.error("Failed to save session for user {}: {}", userId, e.getMessage());
        }
    }

    public Map<String, Object> getSession(Integer userId) {
        try {
            String key = SESSION_PREFIX + userId;
            Map<Object, Object> entries = redisTemplate.opsForHash().entries(key);
            Map<String, Object> result = new HashMap<>();
            for (Map.Entry<Object, Object> entry : entries.entrySet()) {
                result.put(entry.getKey().toString(), entry.getValue());
            }
            return result;
        } catch (Exception e) {
            log.error("Failed to get session for user {}: {}", userId, e.getMessage());
            return new HashMap<>();
        }
    }

    public void deleteSession(Integer userId) {
        try {
            String key = SESSION_PREFIX + userId;
            redisTemplate.delete(key);
            log.debug("Session deleted for user {}", userId);
        } catch (Exception e) {
            log.error("Failed to delete session for user {}: {}", userId, e.getMessage());
        }
    }

    public boolean sessionExists(Integer userId) {
        try {
            String key = SESSION_PREFIX + userId;
            return Boolean.TRUE.equals(redisTemplate.hasKey(key));
        } catch (Exception e) {
            log.error("Failed to check session for user {}: {}", userId, e.getMessage());
            return false;
        }
    }
}