# skill-01 补服务概述语义

## 输入

- `<输出目录>/<领域>/<服务>/01-服务概述.toon`（骨架，含 `[待AI补充]`）

## 任务

读骨架，补全 `[待AI补充]` 字段，输出**完整结构**的 json（json2toon 整体覆盖，必须保留骨架字段，只改语义字段）：

- `service_info.description`：一句话服务定位
- `service_info.core_responsibilities`：3-5 条核心职责（数组）
- 每个场景的 `name`（语义名）和 `desc`（一句话描述）

保留 `id` / `entry_class` / `trigger` / `name` / `domain` 等骨架字段不变。

## 输出

```bash
python kbflow.py json2toon --json-file 概述.json --out <输出目录>/<领域>/<服务>/01-服务概述.toon
```

完整结构示例：

```json
{"service_info":{"name":"stock-service","domain":"库存","description":"一句话定位","core_responsibilities":["职责1","职责2","职责3"]},"scenarios":{"P0":[{"id":"SC-001","entry_class":"StockServiceImpl","name":"语义名","trigger":"dubbo","desc":"一句话描述"}],"P1":[],"P2":[]}}
```
