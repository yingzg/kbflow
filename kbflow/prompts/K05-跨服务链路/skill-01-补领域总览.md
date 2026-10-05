# skill-01 补领域总览语义

## 输入

- `<输出目录>/<领域>/01-领域总览.toon`（骨架，含 `[待AI补充]`）

## 任务

读骨架，补全 `[待AI补充]` 字段，输出**完整结构**的 json（json2toon 整体覆盖，保留骨架字段）：

- `description`：一句话领域定位
- `scope`：领域边界描述（包含什么能力、不含什么）
- 每个业务进程的 `steps`：核心步骤链路

保留 `domain` / `services` / `business_processes` 的 `name` / `services` / `entry_api` 等骨架字段不变。

## 输出

```bash
python kbflow.py json2toon --json-file 总览.json --out <输出目录>/<领域>/01-领域总览.toon
```
