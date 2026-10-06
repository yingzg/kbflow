# skill-01 补服务定位语义

## 输入

- `<输出目录>/<服务>/service-meta/服务元信息.toon`（骨架，含 `[待AI补充]`）

## 任务

读骨架，补全 `[待AI补充]` 字段，输出**完整结构**的 json（json2toon 整体覆盖，保留骨架字段）：

- `identity.description`：一句话服务定位
- `identity.core_responsibilities`：3-5 条核心职责（数组）

保留 `identity.name` / `domain_coverage` / `modules` / `entry_stats` 等骨架字段不变。

## 输出

```bash
python3 .kbflow/kbflow.py json2toon --json-file 元信息.json --out <输出目录>/<服务>/service-meta/服务元信息.toon
```
