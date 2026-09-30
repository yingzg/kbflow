package com.example.wms.transfer;

import org.apache.dubbo.config.annotation.DubboService;
import org.springframework.beans.factory.annotation.Autowired;

@DubboService
public class TransferServiceImpl implements TransferService {

    @Autowired
    private TransferManager transferManager;

    @Override
    public TransferOrder createTransfer(String sku, int qty, String targetWarehouse) {
        return transferManager.create(sku, qty, targetWarehouse);
    }

    @Override
    public void approveOrder(String transferNo, String approver) {
        transferManager.approve(transferNo, approver);
    }

    @Override
    public void confirmTransfer(String transferNo) {
        transferManager.confirm(transferNo);
    }

    @Override
    public TransferOrder getTransferDetail(String transferNo) {
        return transferManager.getDetail(transferNo);
    }

    @Override
    public void cancelOrder(String transferNo) {
        transferManager.cancel(transferNo);
    }

    @Override
    public String toString() {
        return "TransferServiceImpl{}";
    }
}
