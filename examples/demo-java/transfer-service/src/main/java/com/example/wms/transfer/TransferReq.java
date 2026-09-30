package com.example.wms.transfer;

public class TransferReq {

    private String sku;
    private int qty;
    private String targetWarehouse;

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
}
