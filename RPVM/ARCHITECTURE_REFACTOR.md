# RPVM 架构重构方案

## 1. 背景与问题

### 1.1 当前架构问题

原RPVM架构存在以下问题：

1. **Planner模块职责过重**：集中了Judge判断、Plan生成、Generate最终生成三个功能，对LLM来说过于复杂
2. **Memory模块功能不清晰**：未区分证据记忆和路径记忆，导致Planner在第二轮迭代中经常生成重复的已验证子问题
3. **模块功能杂糅**：Verify和Memory的边界不明确，存在功能重复

### 1.2 重构目标

- 拆分Planner的Generate功能，单独作为独立模块
- 统一Memory设计：既是验证过的证据（Golden Evidence），也是推理路径的上下文记录
- 明确各模块边界，避免功能杂糅

---

## 2. 重构后架构

### 2.1 核心模块

| 模块 | 核心职责 |
|------|----------|
| **Planner** | Judge判断 + Plan生成（两次LLM调用） |
| **Verifier** | 仅做检索 + 判断（Rewrite + Retrieve + Verify） |
| **Memory** | 知识压缩 + 证据绑定（LLM调用） |
| **Generate** | 基于已验证路径生成最终答案 |

### 2.2 统一记忆设计

**Memory = Golden Evidence + 上下文路径**（二者统一）

| 内容 | 说明 |
|------|------|
| 精炼路径知识 | 与原始问题Q相关的、可用于后续推理的路径级别知识 |

**核心思想**：Memory中存储的既是验证过的证据（Golden Evidence），也是推理路径的上下文记录（上下文路径）。二者合一，精炼为可直接用于推理的知识单元。

---

## 3. 详细流程

### 3.1 整体流程图

```
┌─────────────────────────────────────────────────────────────────────┐
│                           迭代开始                                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Planner (2次LLM)                             │
├─────────────────────────────────────────────────────────────────────┤
│  输入: Question + Memory                                            │
│                                                                        │
│  [Step 1: Judge]                                                     │
│    Prompt: "基于当前记忆，是否能回答问题?"                           │
│    → YES: 进入Generate模块                                          │
│    → NO:  进入Step 2                                                │
│                                                                        │
│  [Step 2: Plan] (仅Judge=NO时)                                      │
│    Prompt: "基于已有路径，下一步需要查什么?"                         │
│    输出: 下一个Plan                                                 │
└─────────────────────────────────────────────────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │ Plan                           YES → Generate
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           Verifier                                   │
├─────────────────────────────────────────────────────────────────────┤
│  输入: Question + Plan                                              │
│                                                                        │
│  [Step 1: Rewrite]                                                  │
│    从Q+Plan提取检索词（去除Plan中的可能幻觉）                        │
│                                                                        │
│  [Step 2: Retrieve]                                                 │
│    基于优化后的检索词召回Top-K文档                                   │
│                                                                        │
│  [Step 3: Verify]                                                   │
│    Plan vs 文档 → 判断verdict                                       │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │ supported             │ contradicted           │ insufficient
        ▼                       ▼                       ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│   Memory          │  │   Memory          │  │   不触发Memory    │
│   (触发记忆)      │  │   (触发记忆)      │  │   回到Planner     │
└───────────────────┘  └───────────────────┘  └───────────────────┘
        │                       │
        │ 知识压缩+证据绑定     │ 尝试改正+精炼
        │                       │
        ▼                       ▼ 短路当前轮
┌───────────────────────────────────────────────────────────────┐
│                       Memory 模块                              │
├───────────────────────────────────────────────────────────────┤
│  触发条件: Verdict=supported 或 contradicted                  │
│  输入: Question + Plan + Docs + 当前Memory                    │
│  核心: LLM调用进行知识压缩 + 证据绑定                         │
│  输出: 路径级别的精炼知识（可直接用于后续推理）                │
│  存储: 追加到Memory中                                               │
│                                                                       │
│  [示例]                                                         │
│  原始Plan: The director is Mart Crowley                        │
│  Docs验证: 实际导演是Joe Mantello                               │
│  Memory精炼:                                                    │
│    第一跳推理: The director of "The Boys In The Band" (2020)  │
│                is Joe Mantello.                                │
│                                                                       │
│  [supported情况]                                               │
│    输入: 正确Plan + 相关Docs + 当前Memory                      │
│    任务: 从Docs中提取证据，绑定到Plan，压缩精炼                │
│                                                                       │
│  [contradicted情况]                                            │
│    输入: 错误Plan + 相关Docs + 当前Memory                      │
│    任务: 参考错误Plan的逻辑方向 + Docs + 已有路径             │
│          推断正确的Plan并进行精炼                               │
└───────────────────────────────────────────────────────────────┘
                                │
                                │ 返回迭代开始
                                ▼
                    ┌───────────────────────────┐
                    │    Planner重新Judge判断   │
                    └───────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │                           ANSWER_READY
              ▼
        ┌─────────────────────────────┐
        │         Generate            │
        │ 输入: Question + Memory     │
        │ 输出: 最终答案              │
        └─────────────────────────────┘
```

### 3.2 迭代终止条件

| 条件 | 处理 |
|------|------|
| Judge=YES | 转入Generate模块 |
| 达到max_iter | Generate基于当前Memory生成尽力答案 |

---

## 4. 模块详细设计

### 4.1 Planner模块

**输入**: Question + Memory

**Step 1: Judge (LLM调用)**
- 功能: 判断当前记忆是否足以回答问题
- 输出: "YES" 或 "NO"

**Step 2: Plan (LLM调用，仅Judge=NO时)**
- 功能: 基于已有路径生成下一步需要查询的子问题
- 约束: 不能生成已验证过的plan

### 4.2 Verifier模块

**输入**: Question + Plan

**Step 1: Rewrite**
- 功能: 从Question和Plan中提取权威实体，生成不含Plan幻觉的检索词

**Step 2: Retrieve**
- 功能: 使用优化后的检索词召回Top-K文档

**Step 3: Verify**
- 功能: 对比Plan与检索到的文档，输出verdict
- verdict类型:
  - `supported`: Plan被证据支持
  - `contradicted`: Plan被证据反驳
  - `insufficient`: 证据不足

### 4.3 Memory模块

**输入**: Question + Plan + Docs + 当前Memory

**核心逻辑**:
- 仅当verdict=supported或contradicted时触发
- 调用LLM进行知识压缩和证据绑定
- 输出精炼后的路径知识

**Memory精炼的目标**:
将Plan + Docs转化为**可直接用于后续推理的路径级别精炼知识**，格式如：
```
[路径级别精炼知识]
第一跳推理: The director of "The Boys In The Band" (2020) is Joe Mantello.
```

**两种情况**:

| 情况 | 输入 | Memory LLM任务 | 输出示例 |
|------|------|----------------|----------|
| supported | 正确Plan + 相关Docs + 当前Memory | 从Docs中提取证据，绑定到Plan，压缩精炼为与Q相关的路径知识 | 第一跳推理: The director is Joe Mantello. |
| contradicted | 错误Plan + 相关Docs + 当前Memory | 参考错误Plan的逻辑方向 + Docs + 已有路径，推断正确的Plan并进行精炼 | 第一跳推理: The director is Joe Mantello. (而非原假设的Mart Crowley) |

**关键特性**:
- 精炼后的记忆是**可直接作为推理上下文的路径知识**，不是原始假设的简单存储
- Planner能够识别Memory中已有的路径信息，从该路径的下一跳继续推理
- 不一定是推理起点，也可能是中间推理结果

**存储**: 累积到Memory中

### 4.4 Generate模块

**输入**: Question + Memory

**功能**: 基于已验证的完整路径知识生成最终答案

---

## 5. 设计要点

### 5.1 Memory不展示verdict

Memory中存储的全是经过验证的正确路径，verdict信息冗余，无需展示。

### 5.2 记忆添加顺序

按照验证成功的顺序累积，有效路径自动积累。

### 5.3 contradicted处理

1. 将错误Plan和相关Docs传给Memory
2. Memory LLM结合已有路径，尝试改正并精炼
3. 触发短路，避免错误累积

### 5.4 insufficient处理

1. 不触发Memory更新
2. 回到Planner，尝试新的可能
3. 直到达到max_iter

### 5.5 Memory压缩粒度

采用高频压缩策略，每次验证成功都进行压缩。

### 5.6 Memory LLM输入

- 不需要包含之前所有Plan（Memory中已有）
- 必须参考已有路径进行连贯性判断

---

## 6. 与原ReSP论文对比

| 方面 | ReSP论文 | 本重构方案 |
|------|----------|------------|
| Summarizer | 双重功能（Global+Local） | 简化为单一Memory模块 |
| Retriever | 单次检索 | 支持Rewrite优化检索词 |
| Reasoner | Judge+Plan合二为一 | Judge+Plan拆分为两次LLM调用 |
| Generator | 独立模块 | 从Planner中拆分出 |
| Memory | 两个队列（分离设计） | 统一记忆：既是Evidence又是路径 |
