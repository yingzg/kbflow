package com.example.wms.transfer;

import com.example.stock.StockService;
import org.apache.dubbo.config.annotation.DubboReference;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/**
 * 调拨业务编排：事务边界 + 领域逻辑
 */
@Service
public class TransferManager {

    @Autowired
    private TransferOrderMapper transferOrderMapper;

    @DubboReference
    private StockService stockService;

    /** 创建调拨单 */
    public TransferOrder create(String sku, int qty, String targetWarehouse) {
        TransferOrder order = new TransferOrder();
        order.setSku(sku);
        order.setQty(qty);
        order.setTargetWarehouse(targetWarehouse);
        order.setStatus("DRAFT");
        transferOrderMapper.insert(order);
        return order;
    }

    /** 审批调拨单 */
    public void approve(String transferNo, String approver) {
        TransferOrder order = transferOrderMapper.selectByNo(transferNo);
        order.setStatus("APPROVED");
        transferOrderMapper.update(order);
    }

    /** 确认调拨单：加分布式锁防并发，扣减库存 */
    @DistributedLock(keyPath = "transferNo", prefix = "transfer:lock", waitTime = 5, leaseTime = 10)
    public void confirm(String transferNo) {
        TransferOrder order = transferOrderMapper.selectByNo(transferNo);
        stockService.deductStock(order.getSku(), order.getQty());
        order.setStatus("CONFIRMED");
        transferOrderMapper.update(order);
    }

    /** 查询调拨单详情 */
    public TransferOrder getDetail(String transferNo) {
        return transferOrderMapper.selectByNo(transferNo);
    }

    /** 取消调拨单 */
    public void cancel(String transferNo) {
        TransferOrder order = transferOrderMapper.selectByNo(transferNo);
        order.setStatus("CANCELLED");
        transferOrderMapper.update(order);
    }

    /** 校验库存是否充足 */
    public void checkStock(String sku, int qty) {
        int available = stockService.getAvailableStock(sku);
        if (available < qty) {
            throw new RuntimeException("库存不足");
        }
    }

    // 以下是无业务语义的访问器，应被方法过滤降权或过滤
    public String getName() {
        return this.getClass().getSimpleName();
    }

    public int getStatus() {
        return 1;
    }
}
