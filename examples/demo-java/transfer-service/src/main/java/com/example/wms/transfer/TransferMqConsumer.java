package com.example.wms.transfer;

import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.stereotype.Component;

/**
 * 调拨单消息消费者
 */
@Component
@RocketMQMessageListener(topic = "transfer-order-event", consumerGroup = "transfer-consumer")
public class TransferMqConsumer implements RocketMQListener<String> {

    @Override
    public void onMessage(String message) {
        // 处理调拨单事件
    }
}
