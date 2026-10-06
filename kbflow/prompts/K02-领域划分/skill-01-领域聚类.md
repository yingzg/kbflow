# skill-01 领域聚类

## 输入

读 `<输出目录>/service-meta/behavior.toon` 的全部业务入口（注意每个入口的 `class_name` / `package` / `doc` / `methods`）。

## 任务

把全部入口聚类成 5-8 个业务领域（限界上下文级别）。约束：

1. 领域是「一组内聚的业务能力」，不要切成过细的功能模块。
2. 技术性通用能力（枚举、字典、文件上传下载、日志、权限）归入「公共支撑」领域。
3. 纯查询/工作台/汇总统计类入口，归入其所属业务域，不单独成领域。

每个领域输出：领域名、一句话职责、核心实体、边界内能力、边界外能力。

## 输出

输出 json 数组，写文件：

```bash
python3 .kbflow/kbflow.py json2toon --json-file 领域建议.json --out <输出目录>/service-meta/domain_suggestion.toon --wrap domains
```

注意：多值字段用 `|` 拼接成字符串，不要用数组（toon 不支持嵌套数组）：

```json
[{"name":"库存","responsibility":"库存查询与扣减","key_entities":"库存|库存记录","boundary_included":"库存查询|扣减","boundary_excluded":"调拨"}]
```
