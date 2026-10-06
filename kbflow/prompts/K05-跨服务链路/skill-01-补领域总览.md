# skill-01 补领域总览语义

## 输入

- `<输出目录>/<领域>/01-领域总览.toon`（骨架，含 `[待AI补充]`）

## 任务

读骨架，补全 `[待AI补充]` 字段，输出**完整结构**的 json（json2toon 整体覆盖，保留骨架字段）：

- `domain_info.description`：一句话领域定位
- `domain_info.scope`：领域边界描述（包含什么能力、不含什么）
- `core_capabilities`：按「基础操作类 / 查询统计类 / 生命周期类 / 业务协同类」四类归纳该领域的核心能力
- `services[].description` / `services[].responsibility_boundary`：服务定位与职责边界
- 每个业务进程的 `name`（语义名，覆盖骨架的类名占位）和 `steps`（核心步骤链路）

保留 `metadata` / `domain_info.name` / `business_processes` 的 `entry_api` / `navigation_guide` 等确定性字段不变。

## 输出

```bash
python3 .kbflow/kbflow.py json2toon --json-file 总览.json --out <输出目录>/<领域>/01-领域总览.toon
```

完整结构示例（`core_capabilities` 用数组，每条「类别：能力描述」）：

```json
{"metadata":{"domain":"结算管理","service_count":1},"domain_info":{"name":"结算管理","description":"一句话定位","scope":"边界描述"},"core_capabilities":["基础操作类：手工结算申请","查询统计类：结算单查询","生命周期类：开单与票折","业务协同类：支付写回"],"services":[{"id":"S01","name":"mi-intl-scheme","description":"服务定位","layer":"core","responsibility_boundary":"职责边界"}],"business_processes":[{"name":"语义名","services":"mi-intl-scheme","page_name":"-","steps":"核心步骤","entry_api":"SettlementProviderImpl"}],"navigation_guide":{...}}
```
