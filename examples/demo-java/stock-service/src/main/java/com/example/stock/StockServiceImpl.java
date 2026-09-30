package com.example.stock;

import org.apache.dubbo.config.annotation.DubboService;
import org.springframework.beans.factory.annotation.Autowired;

@DubboService
public class StockServiceImpl implements StockService {

    @Autowired
    private StockCacheManager stockCacheManager;

    @Override
    public void deductStock(String sku, int qty) {
        StockRecord record = stockCacheManager.getCached(sku);
        record.setQuantity(record.getQuantity() - qty);
        stockCacheManager.evict(sku);
    }

    @Override
    public int getAvailableStock(String sku) {
        return stockCacheManager.getCached(sku).getQuantity();
    }

    @Override
    public StockRecord getStockRecord(String sku) {
        return stockCacheManager.getCached(sku);
    }
}
