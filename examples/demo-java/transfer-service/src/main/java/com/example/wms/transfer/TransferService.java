package com.example.wms.transfer;

/**
 * @Description 调拨服务：负责调拨单从创建到确认的全生命周期
 */
public interface TransferService {

    /** @Description 创建调拨单 */
    TransferOrder createTransfer(String sku, int qty, String targetWarehouse);

    /** @Description 审批调拨单 */
    void approveOrder(String transferNo, String approver);

    /** @Description 确认调拨单（扣减库存并落库） */
    void confirmTransfer(String transferNo);

    /** @Description 查询调拨单详情 */
    TransferOrder getTransferDetail(String transferNo);

    /** 取消调拨单 */
    void cancelOrder(String transferNo);
}
