package com.example.wms.transfer;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/transfer")
public class TransferController {

    @Autowired
    private TransferService transferService;

    /** 创建调拨单 */
    @PostMapping("/create")
    public TransferOrder create(@RequestBody TransferReq req) {
        return transferService.createTransfer(req.getSku(), req.getQty(), req.getTargetWarehouse());
    }

    /** 查询调拨单详情 */
    @GetMapping("/{id}")
    public TransferOrder detail(@PathVariable("id") String transferNo) {
        return transferService.getTransferDetail(transferNo);
    }
}
