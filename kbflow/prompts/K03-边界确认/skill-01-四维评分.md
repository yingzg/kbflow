# skill-01 四维评分

## 输入

- `<输出目录>/service-meta/behavior.toon`（全部入口）
- `<输出目录>/service-meta/domain_division.toon`（边界矩阵 + 入口归属）

## 任务

对每个入口做四维评分：类名语义 35 / 注释+方法 25 / 包路径 20 / 边界对比 20。

每个入口输出：`entry_id`、`class_name`、`score`（0-100 整数）、`suggested`（KEEP/MOVE/DELETE）、`target_domain`、`decision`（空）、`reason`。score < 70 表示归属不明确。

## 输出

输出 json 数组，写文件：

```bash
python3 .kbflow/kbflow.py json2toon --json-file 评分结果.json --out <输出目录>/service-meta/reviews.toon --wrap reviews
```

json 结构：

```json
[{"entry_id":"API-003","class_name":"TransferController","score":45,"suggested":"MOVE","target_domain":"库存","decision":"","reason":"包路径与注释冲突"}]
```
