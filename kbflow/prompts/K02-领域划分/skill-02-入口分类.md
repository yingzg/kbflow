# skill-02 入口分类

## 输入

- `<输出目录>/service-meta/behavior.toon`（全部入口）
- `<输出目录>/service-meta/domain_suggestion.toon`（已确认的领域清单）

## 任务

把每个业务入口分类到最合适的领域。无法确定的标记 `unclassified`（宁可拒识，不要误识）。

每个入口输出：`entry_id`、`domain`（领域名）、`reason`（类名:业务动作→领域）。

## 输出

输出 json 数组，写文件：

```bash
python kbflow.py json2toon --json-file 入口分类.json --out <输出目录>/service-meta/domain_mapping.toon --wrap domain_mapping
```

json 结构：

```json
[{"entry_id":"API-001","domain_ref":"D1","reason":"StockServiceImpl→库存"}]
```

注意：`domain_ref` 用边界矩阵里的领域 id（D1/D2…），不是领域名。
