# KBFlow

把大型 Java 代码库自动转成「结构化领域知识库」的工具，作为 AI 的「项目记忆」。解决 AI 理解几十万行业务系统时的上下文缺失问题。

## 定位

知识库是**业务定位层（地图）**，不是答案层（画像）。它回答「这是哪块业务、涉及哪个类哪个方法」，把复杂细节交给代码检索，以源代码为准是最高准则。

## 核心思路

> **脚本提取事实，AI 理解语义，TOON 衔接。**

确定性工作交给脚本（零 token 成本、可重复），语义归纳交给 AI（脚本做不到的归纳与判断），两者用紧凑的 TOON 格式衔接。

三个关键设计：

1. **三桶模型**：每个字段分类——🅰 机械可算（脚本填真值）/ 🅱 粗启发式（脚本填猜测）/ 🅲 纯语义（`[待AI补充]` 占位）。脚本锁格式、保数量、不漏，AI 只填语义。
2. **四档门禁**：自动修复 / 硬阻断 / 告警继续 / 人工裁决，每个阶段收尾有明确校验。
3. **派生 vs 校验**：TOON 是唯一真相源；导航/自然语言文档是派生视图，每次重生成，保证地图永远和知识一致。

## 架构：AI IDE 驱动（Prompt 即程序）

KBFlow 是「AI IDE 驱动」的框架，分两层：

```
kbflow/prompts/           ← 流程编排 + AI 语义指令（K01-K08 主流程 + skill 子文档）
kbflow/scanners/ + tools  ← 确定性事实提取 + 工具命令
```

- **md Prompt 文档做「编排」**：主流程只写「读什么 → 调什么脚本 → 调什么 skill → 门禁 → 暂停点」，AI 语义的实现放在 `skill-*.md` 子文档里。
- **脚本做「事实」**：扫描器提取类名、注释、方法、表结构、依赖关系——确定性、可重复。
- **AI IDE 做「语义」**：读 md 文档，理解流程，聚类领域、评分、补服务概述。

读写约定（省 token + 防错）：

- **读**：AI 直接读 `.toon` 紧凑格式（比 JSON 省 40-60% token）
- **写**：AI 输出 json，用 `json2toon` 命令转 toon 落盘（AI 手写 toon 易错）

## 用法

### 1. 初始化知识库 + 同步框架

```bash
python kbflow.py init /path/to/my-kb --project /path/to/java-project   # 初始化 + 注册项目路径
python kbflow.py sync /path/to/my-kb     # 同步 KBFlow 框架（prompts + 工具）到 /path/to/my-kb/.kbflow/
```

`--project` 把 Java 项目路径注册到 `projects.toon` 的 `directories` 区块，后续 K01 读它获取项目路径，无需重复输入。

框架和知识库**分离**：KBFlow 框架（本仓库的 prompts + 工具）通过 `sync` 分发到知识库项目的 `.kbflow/`，知识库项目（产物）和框架（怎么构建）各自独立。

### 2. 开启流程（@ kb_starter.md，每阶段一个窗口）

在 AI IDE（opencode / codex / claude code）里，`@` 启动文档：

```
@/path/to/my-kb/.kbflow/prompts/kb_starter.md
```

AI 读启动文档 → 检测断点 → 执行当前阶段（如 K01）→ 完成后停下来。你按 Enter 关闭窗口，开新窗口重新 `@` 同一个 `kb_starter.md`，AI 断点续跑下一阶段（K02）→ ... 直到 K08。

**全流程只 @ 一个 `kb_starter.md`**，但每个阶段一个窗口（上下文隔离）。断点续跑靠产物文件检测：某个阶段产物已存在则跳过。

### 3. 确定性工具命令（AI 通过 md 文档调用）

| 命令 | 作用 |
|---|---|
| `init <知识库目录>` | 初始化知识库目录（绝对或相对路径） |
| `scan <project> -o <out>` | K01 事实扫描（纯脚本） |
| `json2toon --json-file F --out F [--wrap key]` | AI 输出 json → 转 toon 落盘（写路径） |
| `matrix --domains F --out F` | 领域建议 → 边界矩阵 |
| `checklist gen/parse` | 评分→复核清单 md / 复核清单→决定 toon |
| `skeleton <kind> --domain D --service S -o O` | 骨架生成（overview/interface/data-model/domain-overview/cross-links/service-meta/tech-config/dev-standards） |
| `seal --domain D --service S -o O` | 事实密封（入口清单 + 表清单） |
| `panorama --matrix F --service S --out F` | 领域依赖全景图 |
| `sync <kb_dir>` | 框架→知识库同步 |

运行测试：

```bash
python -m pytest
```

## 修改约定（维护 KBFlow 时）

- 改流程顺序 / 门禁 / 暂停点 → 改主 md 文档
- 改某个 AI 语义的具体做法（prompt、输出格式）→ 改对应 skill md 文档
- 改事实提取逻辑 → 才改脚本（scanners / tools）

## 三个差异化改进

1. **消除静默丢失**：扫不到就告警/失败，不静默跳过；「扫描到的入口 100% 进文档」完整性校验 + 「切分前后数量守恒」校验 + 方法截断告警 + unresolved 落盘。
2. **四档门禁标准化**：自动修复 / 硬阻断 / 告警继续 / 人工裁决，每阶段收尾明确校验（含「占位符残留硬阻断」）。
3. **缓存 Key / 锁 Key / 幂等键 / 分片键统一扫描**：本质是同一件事——提取代码里所有「携带业务实体的字符串模板」，统一模式化成 `{变量}` 占位符模板。

## 目录结构

```
kbflow.py                  # CLI 入口
kbflow/
  prompts/                 # md Prompt 文档（K01-K08 主流程 + skill 子文档）
  scanners/                # 确定性扫描器（事实提取）
  tools.py                 # 确定性工具命令（json2toon/matrix/checklist/skeleton/seal/panorama）
  gates/                   # 门禁体系（四档）
  stages/                  # 事实层函数（骨架生成/格式转换/表映射）
  toon/                    # TOON 编解码
  glossary/                # 业务名词提取（确定性）
  sync/                    # 框架→知识库同步
tests/                     # 测试（pytest）
examples/
  demo-java/               # 示例 Java 项目
  demo-kb/                 # 跑出来的知识库产物
```

## 设计文档

见 [DESIGN.md](DESIGN.md)：设计决策 + 三个差异化改进 + 已知优化方向。
