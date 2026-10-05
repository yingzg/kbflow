# skill-01 补服务概述语义

## 输入

- `<输出目录>/<领域>/<服务>/01-服务概述.toon`（骨架，含 `[待AI补充]`）

## 任务

读骨架，补全 `[待AI补充]` 字段，输出**完整结构**的 json（json2toon 整体覆盖，保留骨架字段）：

- `service_info.description`：一句话服务定位
- `service_info.core_responsibilities`：3-5 条核心职责（数组）
- `service_boundaries.owns`：该服务自己负责的能力（`{capability, description}` 数组）
- `service_boundaries.delegates_to`：委托给外部系统的能力（`{service, capability, usage}` 数组）
- `service_boundaries.provides_to`：提供给其他服务的能力（`{service, capability, interface}` 数组）
- `dependencies.upstream` / `dependencies.downstream`：上下游依赖（`{service, interface, trigger, description}` 或 `{service, capability, usage}` 数组）
- `dependencies.mq_upstream` / `dependencies.mq_downstream`：MQ 消息依赖（`{topic, producer/consumer, description}` 数组）
- 每个场景的 `name`（语义名）和 `desc`（一句话描述）

保留 `service_info.name` / `domain` / 场景的 `id` / `entry_class` / `trigger` 等骨架字段不变。

## 输出

```bash
python kbflow.py json2toon --json-file 概述.json --out <输出目录>/<领域>/<服务>/01-服务概述.toon
```

完整结构示例：

```json
{"service_info":{"name":"mi-intl-scheme","domain":"结算管理","description":"一句话定位","core_responsibilities":["职责1","职责2"]},"service_boundaries":{"owns":[{"capability":"结算单管理","description":"结算单创建与查询"}],"delegates_to":[{"service":"RMS系统","capability":"付款同步","usage":"同步付款信息"}],"provides_to":[]},"dependencies":{"upstream":[],"downstream":[{"service":"RMS系统","capability":"结算付款同步","usage":"SettlementPaymentSyncToRmsTask"}],"mq_upstream":[],"mq_downstream":[]},"scenarios":{"P0":[{"id":"SC-001","entry_class":"SettlementProviderImpl","name":"语义名","trigger":"dubbo","desc":"一句话描述"}],"P1":[],"P2":[]}}
```
