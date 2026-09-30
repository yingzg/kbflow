package com.example.stock;

/**
 * @Description 库存服务：负责库存查询与扣减
 */
public interface StockService {

    /** @Description 扣减库存 */
    void deductStock(String sku, int qty);

    /** @Description 查询可用库存 */
    int getAvailableStock(String sku);

    /** 查询库存记录 */
    StockRecord getStockRecord(String sku);
}
