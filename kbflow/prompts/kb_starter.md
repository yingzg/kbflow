# KBFlow 知识库构建 Prompt

按下面的步骤执行，构建 Java 项目的知识库。**每个阶段执行完成后停下，等用户开新窗口继续下一阶段。**

## 执行前置条件

- 框架已通过 `sync` 同步到知识库的 `.kbflow/` 目录
- 本文件位于 `.kbflow/prompts/kb_starter.md`

## 执行步骤

### 步骤 1：确定知识库目录和项目路径

本 Prompt 文件位于 `<知识库目录>/.kbflow/prompts/kb_starter.md`。**知识库目录 = 本文件所在目录往上推两级**（`prompts/` → `.kbflow/` → 知识库目录）。用你的工作目录工具确认本文件的绝对路径，即可得到知识库目录。

读取 `<知识库目录>/projects.toon` 的 `directories` 区块，获取已注册的 Java 项目路径（父目录 + 项目名）。

如果 `directories` 为空，提示用户：「请先用 `python kbflow.py init <知识库目录> --project <Java项目路径>` 注册项目」。

### 步骤 2：检测当前阶段（断点续跑）

检查输出目录下的产物文件，按顺序确定第一个缺失的阶段：

- `service-meta/behavior.toon` 缺失 → K01
- `service-meta/domain_division.toon` 缺失 → K02
- `service-meta/review_decisions.toon` 缺失 → K03
- `<领域>/<服务>/01-服务概述.toon` 缺失 → K04
- `<领域>/01-领域总览.toon` 缺失 → K05
- `<服务>/service-meta/服务元信息.toon` 缺失 → K06
- `ai/index.toon` 缺失 → K07
- `<领域>/<服务>/_overview.md` 缺失 → K08

### 步骤 3：执行当前阶段

读当前阶段的 Prompt 文档（本目录下的 `K0X-xxx.md`），按文档执行（调脚本 + 产出产物）。

### 步骤 4：完成后停下

输出：

```
✅ 第 X 阶段完成。请按 Enter 关闭本窗口，开新窗口重新 @ kb_starter.md 继续下一阶段。
```

## 注意

- 每个窗口只执行一个阶段，不要连续执行多个阶段。
- 每个阶段只读该阶段需要的产物文件，不要把全部产物读进上下文。
