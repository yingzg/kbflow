# KBFlow 使用指南（真实项目试用）

> 本文是面向**真实项目**的实操手册。建议先花 5 分钟用 demo 验证环境，再按第 3 节的流程跑你自己的项目。

---

## 一、环境准备

- Python 3.10+
- 一个 OpenAI 兼容的 LLM API（K02 领域划分及之后的语义阶段需要；`scan` 纯脚本不需要）

```bash
# 方式一：环境变量（当前 shell 生效）
export KBFLOW_LLM_API_KEY="sk-..."                       # 必填
export KBFLOW_LLM_MODEL="gpt-4o-mini"                    # 可选，默认 gpt-4o-mini
export KBFLOW_LLM_BASE_URL="https://api.openai.com/v1"   # 可选，默认 OpenAI

# 方式二：.env 文件（在运行目录放一个 .env，内容一行一个 KEY=VALUE）
# 或放家目录 ~/.kbflow.env，这样不用每次 export

# 方式三：配置文件（推荐，跨项目共享，无需每次 export）
# 放在 ~/.kbflow/config.ini，内容如下
```

**配置文件方式（推荐）**：建 `~/.kbflow/config.ini`：

```ini
[llm]
api_key = sk-xxxx
base_url = https://api.openai.com/v1
model = gpt-4o-mini
```

- `base_url` 填你用的服务地址（任何 OpenAI 兼容接口都行：OpenAI 官方、DeepSeek `https://api.deepseek.com/v1`、或其他中转服务）
- `model` 填该服务支持的模型名（DeepSeek 用 `deepseek-chat`，OpenAI 用 `gpt-4o` 等）
- **key / base_url / model 三者必须配套**，指向同一个服务

**读取优先级**：环境变量 > `.env` 文件 > `config.ini` 配置文件 > 默认值。

> **「配置了但提示没 key」的排查**：优先用 `.env` 文件（放 KBFlow 根目录或 `~/.kbflow.env`），因为环境变量可能因为 shell 不同、没 source 而没传到 Python 进程。程序会按「环境变量 → 运行目录 .env → ~/.kbflow.env」顺序读取。
>
> **模型选择建议**：`divide`（领域划分）要一次读大量入口，建议用长上下文 + 强推理的模型（如 gpt-4o / claude-sonnet 级别）。`gpt-4o-mini` 跑 demo 够用，跑大型真实项目时领域聚类质量会下降。

---

## 二、5 分钟快速验证（先确认工具能跑）

```bash
cd KbFlow

# 1. 跑内置 demo（纯脚本，无需 LLM）
python kbflow.py scan examples/demo-java -o /tmp/demo-kb

# 预期输出：
#   扫描完成: examples/demo-java
#   入口数: 5
#   产物: behavior, external_dependencies, topology, ddl, key_templates

# 2. 查看产出的 K01 事实
cat /tmp/demo-kb/service-meta/behavior.toon
```

如果第 1 步跑通，说明环境和工具都 OK，可以进入真实项目。

---

## 三、真实项目完整流程

> **核心建议：不要一次扫整个仓库，先以「单个服务」为粒度扫。**
> 理由：`internal_prefixes`（内部包前缀）是从 `pom.xml` 的 `<parent><groupId>` 推断的。如果你扫的是多服务的 mono-repo 根目录，会把所有服务的 groupId 都当成「内部」，导致 `@DubboReference` 跨服务边被误判。先扫一个服务目录，内部/外部边界才准确。

### 方式一：一条命令，交互式向导（推荐）

```bash
export KBFLOW_LLM_API_KEY="sk-..."   # 先配好 LLM key

python kbflow.py run /path/to/your-service -o my-kb
```

启动后进入**交互式向导**，一步下一步推进 8 个阶段：

```
╔══════════════════════════════════════╗
║      KBFlow 知识库构建向导          ║
╚══════════════════════════════════════╝

━━━━━ [1/8] K01 事实扫描 ━━━━━
  ✅ 发现 5 个业务入口
  按 Enter 继续下一步，输入 q 退出

━━━━━ [2/8] K02 领域划分（LLM） ━━━━━
  LLM 建议领域:
    1. 调拨 - 调拨单生命周期
    2. 库存 - 库存查询与扣减
  🛑 确认领域清单 [Y 采纳 / M 修改 / C 自定义]:   ← 人工裁决点

━━━━━ [3/8] K03 边界确认（LLM 四维评分） ━━━━━
  🛑 低置信度: XxxImpl (score=45)              ← 人工复核点
     [KEEP/MOVE/DELETE]:

  ... [4/8]~[8/8] 自动推进 ...
```

- **只有两处会停**：K02 确认领域清单、K03 低置信度复核——这两处是「人给裁决，机器做苦力」的关键分叉点。
- **其余阶段自动推进**，每个阶段打印结果，你按 Enter 继续。
- 想无人值守跑通（测试/CI）用 `--auto`：跳过所有人工确认，LLM 建议自动采纳。

**断点续跑**：中途中断了，重新 `run` 同一个输出目录即可，已完成的阶段会自动跳过（检测产物文件是否存在），从断点继续——不会重跑耗时的 K01 扫描（`⏭ 已跳过（产物已存在，断点续跑）`）。阶段间靠产物文件交接，天然支持续跑，不需要「重头再来」。

### 方式二：逐命令（细粒度控制，高级用户）

如果你只想跑某一步、或需要细粒度控制，每个阶段也有独立命令：

### 第 0 步：初始化知识库（可选，`run` 会自动做）

```bash
python kbflow.py init my-kb
# 产出 my-kb/projects.toon
```

### 第 1 步：K01 事实扫描（纯脚本，最核心）

```bash
python kbflow.py scan /path/to/your-service -o my-kb
```

产出 5 个文件（`my-kb/service-meta/`）：

| 文件 | 内容 |
|---|---|
| `behavior.toon` | 业务入口（Dubbo/REST/MQ/Job），分离有注释/无注释 |
| `external_dependencies.toon` | 外部依赖（`@DubboReference` + XML） |
| `topology.toon` | 类级依赖拓扑（注入近似，非精确调用链） |
| `ddl.toon` | 数据库表结构 |
| `key_templates.toon` | 锁/缓存/幂等/分片 Key 模板 |

**这一步该做什么**：打开 `behavior.toon` 检查入口清单是否合理——有没有漏扫的入口、有没有扫进「纯技术模块」（common/base 等）的噪音。

> **已知限制（诚实说明）**：当前 `scan` 扫描目录下所有 `.java`（自动跳过 `test`/`target`），**没有** include/exclude 过滤参数。如果你的服务目录里混有非业务模块，建议用服务级目录（`src/main/java` 所在的服务根）作为扫描目标，而不是更大的父目录。

### 第 2 步：K02 领域划分（LLM + 人工确认）

```bash
python kbflow.py divide -o my-kb
```

流程：
1. LLM 读所有入口，生成「领域建议清单」并打印；
2. **🛑 强制暂停点**：你确认清单（`Y` 采纳 / `M` 修改 / `C` 自定义）；
3. 确认后生成 `my-kb/service-meta/domain_boundary_matrix.toon`（边界矩阵）。

> **这是最关键的一步**：领域划分错了，后面全部返工。认真看 LLM 建议的领域名、边界、关键实体是否符合你对业务的理解。`M` 和 `C` 允许你手动改写清单。

### 第 3 步：K03 边界确认（LLM 评分 + 人工复核）

```bash
python kbflow.py confirm -o my-kb
```

流程：对每个入口做四维评分（类名 35 / 注释 25 / 包路径 20 / 边界对比 20），≥70 自动采纳，<70 暂停让你 `KEEP`/`MOVE`/`DELETE`。产出 `my-kb/service-meta/review_decisions.toon`。

### 第 4 步：K04 领域知识（三桶骨架，无 LLM 也能跑骨架）

```bash
python kbflow.py knowledge 库存 stock-service -o my-kb
# 参数：<领域名> <服务名>
```

产出 `my-kb/库存/stock-service/01-服务概述.toon`，这是「三桶骨架」：脚本填好能确定的字段（服务名、入口清单、数量），语义字段留 `[待AI补充]` 占位。

> 骨架生成是纯脚本的；语义补充（填 `[待AI补充]`）当前在 `narrate` 阶段由 LLM 完成（见第 6 步）。

### 第 5 步：K05 跨服务 + K06 元信息 + K07 导航

```bash
# K05 跨服务链路（从 topology 的 external 边生成）
python kbflow.py cross 库存 -o my-kb

# K06 服务元信息（示例类：注释最完整的入口，AI 编码时可模仿）
python kbflow.py meta stock-service -o my-kb

# K07 全局导航（纯派生，每次重生成）
python kbflow.py index -o my-kb
```

### 第 6 步：K08 可读性交付（生成人读文档 + 名词解释）

```bash
python kbflow.py narrate 库存 stock-service -o my-kb
```

产出两个文件（**这是你验证整个工具走完质量的关键**）：

| 文件 | 内容 |
|---|---|
| `my-kb/库存/stock-service/_overview.md` | 自然语言文档（一句话定位 + 服务概述 + 接口清单 + 数据模型） |
| `my-kb/库存/stock-service/_glossary.toon` | 业务名词解释（累积型，可反复迭代增强） |

> **为什么 `_overview.md` 重要**：TOON 是给 AI 读的紧凑格式，人读起来费劲。`_overview.md` 把事实（脚本锁死的接口清单、数据模型）+ 叙述（LLM 写的服务定位）合并成人读文档。**你一眼就能看出「这个服务做什么、有哪些接口、涉及哪些表」有没有缺失或分错**——这就是「走完全流程后人工验证产物质量」的抓手。

---

## 四、如何判断产物质量

走完第 1-6 步后，重点检查这几处：

1. **入口有没有漏**：`behavior.toon` 的 `metadata.entry_count` 是不是符合你预期的入口数量。如果漏了，看是不是注解形态特殊（比如全限定名注解）。
2. **领域分得对不对**：`domain_boundary_matrix.toon` 的领域名和边界是否符合业务直觉。
3. **人读文档通不通**：读 `_overview.md`，服务定位是否准确、接口清单是否完整（脚本锁死的部分不会漏，漏了说明 K01 没扫到）。
4. **Key 模板全不全**：`key_templates.toon` 里锁/缓存 Key 是否都扫到了（这是本工具相对典型方案的差异化点）。

---

## 五、常见问题（FAQ）

**Q1：`scan` 报错或入口数明显偏少？**
确认扫描的是服务根目录（含 `pom.xml` 和 `src/main/java`），而不是某层子目录。`internal_prefixes` 从 `pom.xml` 推断，扫错目录会导致内外判断错误。

**Q2：`divide` 提示 `LLMNotConfiguredError`？**
说明没配 `KBFLOW_LLM_API_KEY`。`scan` 不需要 key，但 K02 起必须有。这是设计上的硬约束——无 key 直接失败，不生成残缺的语义。

**Q3：领域建议不准确怎么办？**
用 `C`（自定义）或 `M`（修改）手动给领域清单。领域划分的「人给先验」是设计的一部分——「有哪些领域」是业务先验，AI 只做「这个类属于哪个领域」的匹配。

**Q4：TOON 文件看不懂？**
正常，TOON 是给 AI 读的紧凑格式。人读的是 `narrate` 生成的 `_overview.md`，以及 `index` 生成的 `领域依赖全景图.md`。

**Q5：方法注释为什么「少」了？**
K01 用「业务方法识别」过滤掉了无业务语义的方法（`toString`/`getName` 等访问器、`check()` 纯校验），优先保留业务动作方法（`approve`/`confirm`/`update`）。这是刻意设计——避免 getter/setter 噪音淹没真正的业务语义。

**Q6：扫描很慢？**
大项目（几十万行）首次 `scan` 是单线程正则扫描，会花几分钟。这是「先用正则把流程跑通」的取舍，AST 并行化是已知优化方向（见 `DESIGN.md`）。

---

## 六、目录速查

| 阶段 | 命令 | 需要 LLM | 产物 |
|---|---|---|---|
| 初始化 | `init` | ❌ | `projects.toon` |
| K01 事实 | `scan <project>` | ❌ | `service-meta/*.toon`（5 个） |
| K02 归属 | `divide` | ✅ | `domain_boundary_matrix.toon` |
| K03 确认 | `confirm` | ✅ | `review_decisions.toon` |
| K04 知识 | `knowledge <域> <服务>` | ❌（骨架） | `{域}/{服务}/01-服务概述.toon` |
| K05 跨服务 | `cross <域>` | ❌ | `{域}/02-跨服务链路.toon` |
| K06 元信息 | `meta <服务>` | ❌ | `{服务}/service-meta/开发规范.toon` |
| K07 导航 | `index` | ❌ | `ai/index.toon` + 全景图 |
| K08 可读性 | `narrate <域> <服务>` | ✅ | `_overview.md` + `_glossary.toon` |
| 同步 | `sync <kb>` | ❌ | 框架→知识库文件同步 |

> 详细设计见 [README.md](README.md) 和 [DESIGN.md](DESIGN.md)。
