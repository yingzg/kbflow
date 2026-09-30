package com.example.stock;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 库存同步定时任务
 */
@Component
public class StockSyncJob {

    /** 每日凌晨同步库存 */
    @Scheduled(cron = "0 0 2 * * ?")
    public void syncStock() {
        // 同步逻辑
    }
}
