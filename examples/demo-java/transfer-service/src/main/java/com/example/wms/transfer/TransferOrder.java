package com.example.wms.transfer;

/**
 * 调拨单实体
 */
public class TransferOrder {

    private String transferNo;
    private String sku;
    private int qty;
    private String targetWarehouse;
    private String status;

    public String getTransferNo() {
        return transferNo;
    }

    public void setTransferNo(String transferNo) {
        this.transferNo = transferNo;
    }

    public String getSku() {
        return sku;
    }

    public void setSku(String sku) {
        this.sku = sku;
    }

    public int getQty() {
        return qty;
    }

    public void setQty(int qty) {
        this.qty = qty;
    }

    public String getTargetWarehouse() {
        return targetWarehouse;
    }

    public void setTargetWarehouse(String targetWarehouse) {
        this.targetWarehouse = targetWarehouse;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
