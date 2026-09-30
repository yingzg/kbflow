from kbflow.scanners.behavior import scan_behavior


def test_dubbo_interface_doc_priority(make_index):
    idx = make_index({
        "TransferService.java": (
            "package com.example;\n"
            "/** @Description 创建调拨单 */\n"
            "public interface TransferService {\n"
            "  /** @Description 审批 */ void approve(String no);\n"
            "}\n"
        ),
        "TransferServiceImpl.java": (
            "package com.example;\n"
            "@DubboService\n"
            "public class TransferServiceImpl implements TransferService {\n"
            "  public void approve(String no) {}\n"
            "}\n"
        ),
    })
    dubbo = scan_behavior(idx)["dubbo"]
    assert len(dubbo) == 1
    assert dubbo[0]["doc"] == "创建调拨单"
    assert dubbo[0]["interface_name"] == "TransferService"


def test_rest_entry_base_path(make_index):
    idx = make_index({
        "TransferController.java": (
            "package com.example;\n"
            "@RestController\n"
            "@RequestMapping(\"/transfer\")\n"
            "/** 调拨接口 */\n"
            "public class TransferController {\n"
            "  @PostMapping(\"/create\") public void create() {}\n"
            "}\n"
        ),
    })
    rest = scan_behavior(idx)["rest"]
    assert len(rest) == 1
    assert rest[0]["base_path"] == "/transfer"
    assert rest[0]["doc"] == "调拨接口"


def test_mq_entry_topic(make_index):
    idx = make_index({
        "TransferMqConsumer.java": (
            "package com.example;\n"
            "@Component\n"
            "@RocketMQMessageListener(topic = \"transfer-order-event\", consumerGroup = \"g\")\n"
            "/** 调拨消息消费者 */\n"
            "public class TransferMqConsumer {\n"
            "  public void onMessage(String m) {}\n"
            "}\n"
        ),
    })
    mq = scan_behavior(idx)["mq"]
    assert len(mq) == 1
    assert mq[0]["topic"] == "transfer-order-event"


def test_job_entry_cron(make_index):
    idx = make_index({
        "StockSyncJob.java": (
            "package com.example;\n"
            "@Component\n"
            "/** 库存同步 */\n"
            "public class StockSyncJob {\n"
            "  @Scheduled(cron = \"0 0 2 * * ?\") public void sync() {}\n"
            "}\n"
        ),
    })
    job = scan_behavior(idx)["job"]
    assert len(job) == 1
    assert job[0]["jobs"][0]["cron"] == "0 0 2 * * ?"
