package com.example.stock;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

/**
 * 库存缓存管理：缓存 Key 携带业务实体
 */
@Component
public class StockCacheManager {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    private static final String STOCK_CACHE_KEY = "stock:cache:";

    /** 读取库存缓存 */
    public StockRecord getCached(String sku) {
        String key = STOCK_CACHE_KEY + sku;
        StockRecord record = (StockRecord) redisTemplate.opsForValue().get(key);
        if (record == null) {
            record = new StockRecord();
            record.setSku(sku);
            redisTemplate.opsForValue().set(key, record, 30, TimeUnit.MINUTES);
        }
        return record;
    }

    /** 失效库存缓存 */
    public void evict(String sku) {
        redisTemplate.delete(STOCK_CACHE_KEY + sku);
    }

    /** 幂等扣减 */
    @Idempotent(key = "#sku", prefix = "stock:idem")
    public void deductIdempotent(String sku, int qty) {
        // 幂等键携带业务实体
    }
}
