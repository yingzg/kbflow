# skill-01 业务名词解释

## 输入

- `<输出目录>/service-meta/behavior.toon`（该领域的入口）
- 第 1 步 seal 输出的入口清单 + 关键实体

## 任务

从入口清单 + 关键实体提取业务名词，给每个名词一句话中文解释（说清楚它是什么，不是做什么）。

## 输出

输出 json 数组，写文件：

```bash
python3 .kbflow/kbflow.py json2toon --json-file glossary.json --out <输出目录>/<领域>/<服务>/_glossary.toon --wrap glossary
```

json 结构：

```json
[{"name":"调拨单","zh":"记录货物从一仓库调往另一仓库的单据"}]
```
