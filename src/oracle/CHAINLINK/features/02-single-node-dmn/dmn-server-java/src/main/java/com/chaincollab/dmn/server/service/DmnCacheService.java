package com.chaincollab.dmn.server.service;

import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

@Service
public class DmnCacheService {

    public static class CachedResult {
        public final String requestId;
        public final String decisionId;
        public final Object value;
        public final String raw;
        public final String hashHex;
        public final String hashDec;
        public final long updatedAt;

        public CachedResult(String requestId, String decisionId, Object value, String raw, String hashHex, String hashDec, long updatedAt) {
            this.requestId = requestId;
            this.decisionId = decisionId;
            this.value = value;
            this.raw = raw;
            this.hashHex = hashHex;
            this.hashDec = hashDec;
            this.updatedAt = updatedAt;
        }
    }

    private final ConcurrentMap<String, CachedResult> cachedResults = new ConcurrentHashMap<>();
    private final ConcurrentMap<String, CachedResult> cachedByHash = new ConcurrentHashMap<>();
    private volatile CachedResult latestResult;

    public CachedResult store(String requestId, String decisionId, Object value, String raw, String hashHex, String hashDec) {
        CachedResult cached = new CachedResult(requestId, decisionId, value, raw, hashHex, hashDec, System.currentTimeMillis());
        latestResult = cached;
        if (requestId != null && !requestId.isEmpty()) {
            cachedResults.put(requestId, cached);
        }
        if (hashHex != null && !hashHex.isEmpty()) {
            cachedByHash.put(hashHex.toLowerCase(), cached);
        }
        if (hashDec != null && !hashDec.isEmpty()) {
            cachedByHash.put(hashDec, cached);
        }
        return cached;
    }

    public CachedResult latest() {
        return latestResult;
    }

    public CachedResult getByRequestId(String requestId) {
        if (requestId == null) {
            return null;
        }
        return cachedResults.get(requestId);
    }

    public CachedResult getByHash(String hash) {
        if (hash == null || hash.isEmpty()) {
            return null;
        }
        return cachedByHash.get(hash.toLowerCase());
    }

    public Map<String, Object> ack(String requestId, Long blockTimestampMs) {
        boolean removedByRequestId = false;
        if (requestId != null && !requestId.isEmpty()) {
            removedByRequestId = cachedResults.remove(requestId) != null;
        }

        boolean clearedLatest = false;
        boolean skippedLatest = false;
        CachedResult cached = latestResult;
        if (cached != null && (requestId == null || requestId.isEmpty() || requestId.equals(cached.requestId))) {
            if (blockTimestampMs != null && cached.updatedAt > blockTimestampMs) {
                skippedLatest = true;
            } else {
                latestResult = null;
                clearedLatest = true;
            }
        }

        return Map.of(
            "ok", true,
            "clearedLatest", clearedLatest,
            "skippedLatest", skippedLatest,
            "removedByRequestId", removedByRequestId
        );
    }
}
