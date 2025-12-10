# ✅ 一、总体思路（核心理念）

**目标：**  
构建一个「先规划推理链，再检索验证，每步验证后更新记忆」的迭代推理框架，  
用**反思-行动-记忆（Reflect–Act–Remember）** 的方式解决多跳问题，  
同时避免重复检索与上下文冗余。

**核心创新点：**

1.  不直接对每步生成-修正，而是**先推理出整体计划链（plan）再逐步验证**。
    
2.  通过**验证过的plan文本拼接形成短期记忆**，用以支撑下一轮规划与回答。
    
3.  当检索不到证据时，通过**rewrite + 扩大检索**，在有限次数内强化召回，而不是直接信任模型。
    
4.  无需复杂的权重、优先级、或多级记忆，保持「简单可复现」。
    

---

# 🧩 二、整体流程框架

## Step 0. 初始化

```makefile
Input: 
    Q = 原始问题
    M = Memory (文本形式, 初始为空)
Parameters:
    max_iter = 3~5   # 最大循环次数
    max_retrieval_attempts = 2  # 每个plan的最大检索尝试次数
```

---

## Step 1. Reflective Planner（反思规划器）

**输入：** Q, M  
**输出：** 一组按逻辑顺序排列的 plan = \[plan₁, plan₂, ...\]

**Prompt逻辑：**

> 结合已有验证过的记忆 M，分析总问题 Q。  
> 若记忆足以回答，直接给出最终答案；否则规划一条逻辑推理链（plan），每一条是可以被验证的自然语言断言。

**例：**

Q:

> What is the name of the fight song of the university whose main campus is in Lawrence, Kansas and whose branch campuses are in the Kansas City metropolitan area?

Planner 输出：

```vbnet
plan1: The university with main campus in Lawrence, Kansas and branch campuses in Kansas City metropolitan area is the University of Kansas.
plan2: The fight song of the University of Kansas is "I'm a Jayhawk".
```

---

## Step 2. Plan Verifier（验证模块）

**输入：** 当前未验证的 planₖ，问题 Q，记忆 M  
**流程：**

1.  检索与 planₖ 相关的文档 docs。
    
    -   若未找到相关文档 → rewrite 检索词并重试。
        
    -   若多次检索仍无结果 → 标记 insufficient，不加入 M。
    
2.  让大模型基于 docs 判断：
    
    -   supported（被证据支持）
        
    -   contradicted（与证据冲突）
        
    -   insufficient（无充分证据）
    
3.  处理结果：
    
    -   **supported** → 将该 plan 精炼后加入 M
        
    -   **contradicted** → 修改为正确版本并加入 M，然后停止当前轮次（因为后续plan可能依赖错误）
        
    -   **insufficient** → 不加入 M，继续验证下一个 plan（若存在）
        

---

## Step 3. Memory 更新

**Memory 形式：**

-   文本拼接形式即可（无需结构化表格）
    
-   例如：
    

```vbnet
Memory:
1. The university with main campus in Lawrence, Kansas is the University of Kansas. (verified)
2. The fight song of the University of Kansas is "I'm a Jayhawk". (verified)
```

**作用：**

-   供下一轮 planner 参考，避免重复检索。
    
-   最终合成答案的上下文。
    

---

## Step 4. 反思与终止条件

-   当 planner 发现当前记忆 M 已足够覆盖回答 Q → 直接生成最终答案。
    
-   或达到最大循环次数 → 输出 best-effort answer，并标记不确定性。
    

---

# ⚙️ 三、完整伪流程（简化实现逻辑）

```python
initialize M = ""
for i in range(max_iter):
    plans = planner(Q, M)

    # 若 planner 认为记忆已足够
    if plans == "ANSWER_READY":
        return generate_final_answer(Q, M)

    for plan in plans:
        for attempt in range(max_retrieval_attempts):
            docs = retrieve(plan)
            if not docs:
                plan = rewrite_retrieval(plan)
                continue

            verdict, corrected_plan, evidence = verify(plan, docs)

            if verdict == "supported":
                M += f"\n{corrected_plan} (verified)"
                break
            elif verdict == "contradicted":
                M += f"\n{corrected_plan} (corrected)"
                break  # 当前轮结束
            else:  # insufficient
                if attempt < max_retrieval_attempts - 1:
                    plan = rewrite_retrieval(plan)
                else:
                    pass  # 放弃该plan
    # 下一轮重新plan
return generate_best_effort_answer(Q, M)
```

---

# 🧠 四、例子演示

### 第 1 轮

**Planner 输出：**

```vbnet
plan1: The university with main campus in Lawrence, Kansas and branch campuses in Kansas City area is the University of Kansas.
plan2: The fight song of the University of Kansas is "I'm a Jayhawk".
```

**Verifier 验证：**

-   plan1 → supported ✅ → 加入 M
    
-   plan2 → contradicted ❌（docs 提示实际是 "Kansas Song"）→ 修正并加入 M → 停止当前轮
    

**Memory 更新：**

```vbnet
M:
1. The university with main campus in Lawrence, Kansas is the University of Kansas. (verified)
2. The fight song of the University of Kansas is "Kansas Song". (corrected)
```

---

### 第 2 轮

Planner 读取 M：

> 已经知道大学是谁 + 战歌是什么  
> → 输出：  
> “Based on the verified facts, the answer is: The fight song is ‘Kansas Song’.”

✅ 终止。

---

# 🔍 五、分析与优点

| 维度 | 优化后框架的特点 |
| --- | --- |
| **推理结构** | Plan → Verify → Memory 循环，自然符合人类推理节奏 |
| **模块数量** | 仅 3 核心模块（Planner, Verifier, Memory） |
| **复杂度** | 去掉了优先级、多级记忆、置信度等繁琐细节 |
| **可解释性** | 每个验证过的 plan 都是“显式证据 + 修改后的事实” |
| **成本控制** | 检索与验证次数可控（max\_retrieval\_attempts, max\_iter） |
| **错误隔离** | 一旦 contradicted，立即短路当前链，防止错误扩散 |
| **避免冗余** | 验证过的信息直接拼接存储，后续重复问题不再检索 |

---

# 📊 六、可扩展性建议（后续优化点）

1.  **Memory 压缩**：每轮结束可让 LLM 对 M 做一次「证据摘要」，保持上下文紧凑。
    
2.  **检索策略自适应**：若连续出现 insufficient，可让模型调整检索方向（site/domain、时间、语言）。
    
3.  **错误纠正学习**：contradicted 断言可存储为“已纠正事实”，防止未来重复错误。
    
4.  **终止条件优化**：可用启发式判断「M 中信息覆盖率 >80% 即停止」。
    

---

## 🧾 七、总结一句话框架说明

> **Reflective Plan-Verify Memory (RPVM)**  
> 大模型先规划推理链，再通过检索验证逐步完善，  
> 将验证过的事实以文本形式存入记忆中，  
> 通过反思循环减少重复检索与上下文冗余，  
> 在有限步内稳定收敛到正确答案。

---

