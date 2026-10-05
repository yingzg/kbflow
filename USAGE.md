# KBFlow 使用指南

> 面向真实项目的实操手册。建议先花 5 分钟用 demo 验证环境，再按第 3 节的流程跑你自己的项目。

---

## 一、环境准备

- Python 3.10+
- 一个 AI IDE（opencode / codex / claude code），用于驱动 K02-K08 的语义阶段

> KBFlow 本身不调 LLM API——**语义由 AI IDE 完成**，KBFlow 的脚本只做确定性事实提取。所以不需要配 API key。

---

## 二、5 分钟快速验证

```bash
cd KbFlow

# 1. 跑内置 demo（纯脚本）
python kbflow.py scan examples/demo-java -o /tmp/demo-kb

# 预期：入口数 5，产物 behavior/external_dependencies/topology/ddl/key_templates/mapper_tables

# 2. 查看 K01 事实
cat /tmp/demo-kb/service-meta/behavior.toon
```

跑通说明环境 OK，可以进入真实项目。

---

## 三、真实项目完整流程（AI IDE 驱动）

> 核心建议：先以「单个服务」为粒度扫，不要一次扫整个多服务 mono-repo 根目录。

### 第 1 步：K01 事实扫描（纯脚本）

```bash
python kbflow.py scan /path/to/your-service -o my-kb
```

产出 `my-kb/service-meta/` 的事实文件：

| 文件 | 内容 |
|---|---|
| `behavior.toon` | 业务入口（Dubbo/REST/MQ/Job） |
| `topology.toon` | 类级依赖拓扑 |
| `ddl.toon` | 数据库表结构 |
| `mapper_tables.toon` | Mapper 类 → 表名映射 |
| `key_templates.toon` | 锁/缓存/幂等/分片 Key 模板 |

**检查**：打开 `behavior.toon` 看入口清单是否合理——有没有漏扫、有没有扫进纯技术模块的噪音。

### 第 2 步：K01-K08 由 AI IDE 驱动（每阶段开新窗口）

在 AI IDE（opencode / codex / claude code）里，**每个阶段开一个新窗口**，`@` 该阶段的 md 文档：

```
# 窗口 1：@kbflow/prompts/K01-事实扫描.md  → scan → 关闭窗口
# 窗口 2：@kbflow/prompts/K02-领域划分.md  → 读 K01 产物 → 聚类 → 关闭窗口
# 窗口 3：@kbflow/prompts/K03-边界确认.md  → 评分 → 关闭窗口
# ... 直到 K08
```

**为什么每阶段开新窗口**：阶段间靠产物文件交接（产物落在磁盘，下一阶段读文件），每个窗口只读「当前阶段 + 上一阶段产物」，上下文短、不溢出。AI 上下文有限，串 8 阶段会溢出——这正是「阶段化」的设计目的。

**只有两处会停**：K02 确认领域清单、K03 低置信度复核——「人给裁决，AI 做苦力」。

**断点续跑**：产物文件已存在就跳过该阶段，中断后从断点阶段重新开窗口即可。

### 确定性工具命令（AI 通过 md 文档自动调用，一般不用手动跑）

| 命令 | 作用 |
|---|---|
| `json2toon --json-file F --out F [--wrap key]` | AI 写 json → 转 toon（写路径，防手写 toon 出错） |
| `matrix --domains F --out F` | 领域建议 → 边界矩阵 |
| `checklist gen/parse` | 评分 → 复核清单 / 复核清单 → 决定 |
| `skeleton <kind> --domain D --service S -o O` | 生成骨架（8 种子命令，带 `[待AI补充]` 占位） |
| `seal --domain D --service S -o O` | 事实密封 |
| `panorama --matrix F --service S --out F` | 领域依赖全景图 |
| `sync <kb_dir>` | 框架→知识库同步 |

---

## 四、如何判断产物质量

1. **入口有没有漏**：`behavior.toon` 的 `metadata.entry_count` 是否符合预期。
2. **领域分得对不对**：`domain_division.toon` 的领域名和边界是否符合业务直觉。
3. **人读文档通不通**：读 `<领域>/<服务>/_overview.md`，服务定位是否准确、接口清单是否完整。
4. **Key 模板全不全**：`key_templates.toon` 里锁/缓存 Key 是否都扫到（差异化点）。

---

## 五、常见问题（FAQ）

**Q1：`scan` 报错或入口数明显偏少？**
确认扫描的是服务根目录（含 `pom.xml` 和 `src/main/java`），不是某层子目录。

**Q2：领域建议不准确？**
用 `M`（修改）或 `C`（自定义）手动给领域清单。领域划分的「人给先验」是设计的一部分。

**Q3：TOON 文件看不懂？**
正常，TOON 是给 AI 读的紧凑格式。人读的是 K08 生成的 `_overview.md` 和 `领域依赖全景图.md`。

**Q4：AI 写 toon 会写错吗？**
不会——AI 只写 json，用 `json2toon` 命令转 toon（脚本负责序列化）。读的时候 AI 直接读 toon（省 token）。

**Q5：扫描慢？**
大项目首次 `scan` 是正则扫描，约 3-5 分钟（已做 O(1) 索引 + 并行读优化）。AST 并行化是已知优化方向（见 DESIGN.md）。

---

## 六、目录速查

| 阶段 | 驱动方式 | 产物 |
|---|---|---|
| K01 事实 | `scan`（脚本） | `service-meta/*.toon` |
| K02 归属 | AI IDE @K02.md | `domain_division.toon` |
| K03 确认 | AI IDE @K03.md | `review_decisions.toon` |
| K04 知识 | AI IDE @K04.md | `{域}/{服务}/01-服务概述.toon` 等 3 份 |
| K05 跨服务 | AI IDE @K05.md | `{域}/01-领域总览.toon` 等 |
| K06 元信息 | AI IDE @K06.md | `{服务}/service-meta/` 3 份 |
| K07 导航 | AI IDE @K07.md | `ai/index.toon` + 全景图 |
| K08 可读性 | AI IDE @K08.md | `_overview.md` + `_glossary.toon` |

> 详细设计见 [README.md](README.md) 和 [DESIGN.md](DESIGN.md)。
