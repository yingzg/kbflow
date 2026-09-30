# KBFlow

把大型 Java 代码库自动转成「结构化领域知识库」的工具，作为 AI 的「项目记忆」。解决 AI 理解几十万行业务系统时的上下文缺失问题。

## 定位

知识库是**业务定位层（地图）**，不是答案层（画像）。它回答「这是哪块业务、涉及哪个类哪个方法」，把复杂细节交给代码检索，以源代码为准是最高准则。

## 核心思路

> **脚本提取事实，AI 理解语义，TOON 衔接。**

确定性工作交给脚本（零 token 成本、可重复），语义归纳交给模型（脚本做不到的归纳与判断），两者用紧凑的 TOON 格式衔接。

三个关键设计：

1. **三桶模型**：每个字段分类——🅰 机械可算（脚本填真值）/ 🅱 粗启发式（脚本填猜测）/ 🅲 纯语义（`[待AI补充]` 占位）。脚本锁格式、保数量、不漏，AI 只填语义。
2. **四档门禁**：自动修复 / 硬阻断 / 告警继续 / 人工裁决，每个阶段收尾有明确校验。
3. **派生 vs 校验**：TOON 是唯一真相源；导航/自然语言文档是派生视图，每次重生成，保证地图永远和知识一致。

## 流水线

```
run（交互式向导，一步下一步）── 内部依次执行：
  scan(K01) → divide(K02) → confirm(K03) → knowledge(K04) → cross(K05)
  → meta(K06) → index(K07) → narrate(K08)
sync(框架→知识库，独立)
```

**推荐用法：一条命令启动向导** `python kbflow.py run <项目路径>`，交互式推进 8 阶段，只在 K02（领域确认）、K03（低置信度复核）两处暂停等人工裁决。每个阶段也有独立命令可单独跑。

| 命令 | 阶段 | 产出 |
|---|---|---|
| `init` | 初始化 | projects.toon |
| `scan` | K01 事实 | 入口/依赖/拓扑/DDL/Key模板（纯脚本） |
| `divide` | K02 归属 | 领域建议 + 边界矩阵（LLM + 人工确认） |
| `confirm` | K03 确认 | 四维评分 + 复核决策（LLM + 人工） |
| `knowledge` | K04 领域知识 | 服务概述/接口链路/数据模型（三桶骨架） |
| `cross` | K05 跨服务 | 领域总览/跨服务链路 |
| `meta` | K06 元信息 | 架构/技术栈/开发规范 |
| `index` | K07 导航 | AI 索引/全景图/使用协议（纯派生） |
| `narrate` | K08 可读性 | glossary + 自然语言文档（累积 + 派生） |
| `sync` | 同步 | 框架→知识库文件同步 |

**阶段间靠产物文件交接**，每个阶段独立命令、可开新窗口跑，天然隔离上下文（AI 的上下文是有限的，串 7 阶段会溢出）。

## 快速开始

```bash
# 1. 配置 LLM（K01 纯脚本不需要，K02 起需要；只需配一次）
python kbflow.py config
#   交互式填入 API Key / Base URL / Model，自动写入 ~/.kbflow/config.ini
#   也可以手动参考项目根目录的 config.example.ini（任何 OpenAI 兼容服务都行）

# 2. 一条命令启动交互式向导，一步下一步构建完整知识库
python kbflow.py run /path/to/java-project -o my-kb

# 或者逐阶段单独跑（细粒度控制）：
python kbflow.py scan /path/to/java-project -o my-kb   # K01 纯脚本
python kbflow.py divide -o my-kb                        # K02 领域划分
python kbflow.py confirm -o my-kb                       # K03 边界确认
python kbflow.py knowledge 调拨 transfer-service -o my-kb  # K04 领域知识
python kbflow.py index -o my-kb                         # K07 全局导航
python kbflow.py narrate 调拨 transfer-service -o my-kb # K08 可读性交付
```

> **LLM 配置说明**：`kbflow.py config` 生成 `~/.kbflow/config.ini`。`api_key` / `base_url` / `model` 三者必须指向同一个服务（OpenAI 官方、DeepSeek、中转服务均可）。读取优先级：环境变量 > `.env` > `config.ini` > 默认值。

运行测试：

```bash
python -m pytest
```

## 三个差异化改进

1. **消除静默丢失**：扫不到就告警/失败，不静默跳过；「扫描到的入口 100% 进文档」完整性校验 + 「切分前后数量守恒」校验 + 方法截断告警 + unresolved 落盘。
2. **四档门禁标准化**：自动修复 / 硬阻断 / 告警继续 / 人工裁决，每阶段收尾明确校验（含「占位符残留硬阻断」）。
3. **缓存 Key / 锁 Key / 幂等键 / 分片键统一扫描**：本质是同一件事——提取代码里所有「携带业务实体的字符串模板」，统一模式化成 `{变量}` 占位符模板。

## 目录结构

```
kbflow.py                  # CLI 入口
kbflow/
  toon/                    # TOON 编解码（唯一真相源格式）
  scanners/                # K01 纯脚本扫描器
  gates/                   # 门禁体系（四档）
  stages/                  # 阶段编排（K01-K08）
  glossary/                # 业务名词解释（累积型知识）
  sync/                    # 框架→知识库同步
tests/                     # 测试（pytest）
examples/
  demo-java/               # 示例 Java 项目
  demo-kb/                 # 跑出来的知识库产物
docs/plans/                # 实现计划
```

## 设计文档

见 [DESIGN.md](DESIGN.md)：设计决策 + 三个差异化改进 + 已知优化方向（AST）。
