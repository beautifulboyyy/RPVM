# RPVM: Reflective Plan-Verify Memory

基于FlashRAG框架实现的RPVM(Reflective Plan-Verify Memory)方法，用于多跳问答任务。

## 📊 当前状态

| 项目 | 状态 |
|------|------|
| 核心代码 | ✅ 完成 |
| E5检索器 | ✅ 已配置 (`e5-base-v2`) |
| 索引构建 | ✅ 小语料库测试完成 (`domainrag_text_corpus.jsonl`) |
| OpenAI API | ✅ 已配置 (`gpt-3.5-turbo`) |
| 流程测试 | ✅ 本地测试通过 |
| 完整实验 | ⏳ 待服务器运行 |

### 本地测试环境
- Windows 10, 16GB内存, 无GPU
- 小语料库: 14,406条文档 (37MB)
- CPU索引构建时间: 约1.5小时

### 待完成
- [ ] 服务器上构建完整维基百科索引 (`wiki18_100w.jsonl`, 2100万条)
- [ ] 2WikiMultihopQA数据集完整实验
- [ ] HotpotQA数据集实验
- [ ] 性能评估与结果分析

## 🗂️ 文件结构

```
RPVM/
├── README.md                 # 本文档
├── PVM.md                    # RPVM方法详细说明
├── 需求文档.md               # 实验需求文档
├── rpvm_config.yaml          # RPVM配置文件
├── rpvm_pipeline.py          # RPVM Pipeline实现
├── run_rpvm_exp.py           # 运行完整实验
├── simple_example.py         # 简单示例脚本
└── output/                   # 实验输出目录(自动创建)
    └── rpvm_experiments/
        ├── intermediate_data.jsonl  # 中间推理数据
        ├── metric_score.txt         # 评估指标
        └── config.yaml              # 保存的配置
```

## 🚀 快速开始

### 1. 环境准备

确保已安装FlashRAG及其依赖：

```bash
cd /path/to/flashRAG
pip install -e .
pip install openai tiktoken  # OpenAI API支持
```

### 2. 配置设置

编辑 `rpvm_config.yaml`，设置以下关键路径：

```yaml
# 数据集路径
data_dir: "datasets"  # 你的FlashRAG数据目录

# E5检索器
retrieval_model_path: "intfloat/e5-base-v2"  # E5模型路径
index_path: "indexes/e5_Flat.index"          # E5索引路径
corpus_path: "indexes/general_knowledge.jsonl"  # 文档库路径

# OpenAI API
openai_setting:
  api_key: null  # 从环境变量读取，或在此填写
  base_url: "https://api.openai.com/v1"
```

### 3. 设置OpenAI API Key

选择以下方式之一：

```bash
# 方式1: 环境变量
export OPENAI_API_KEY='your-api-key-here'

# 方式2: 在rpvm_config.yaml中设置
# openai_setting:
#   api_key: "your-api-key-here"

# 方式3: 命令行传参
python run_rpvm_exp.py --openai_api_key your-api-key-here ...
```

### 4. 运行示例

#### 简单示例 (单个问题)

```bash
cd RPVM
python simple_example.py --mode simple
```

#### 批量示例 (多个问题)

```bash
python simple_example.py --mode batch
```

#### 小规模测试 (5个样本)

```bash
python run_rpvm_exp.py \
    --dataset_name hotpotqa \
    --split test \
    --gpu_id 0 \
    --num_samples 5
```

#### 完整实验

```bash
# HotpotQA数据集
python run_rpvm_exp.py \
    --dataset_name hotpotqa \
    --split test \
    --gpu_id 0

# 2WikiMultihopQA数据集
python run_rpvm_exp.py \
    --dataset_name 2wikimultihopqa \
    --split test \
    --gpu_id 0
```

## 📊 输出结果

运行后会生成以下文件：

### 1. 中间推理数据 (`intermediate_data.jsonl`)

每行是一个样本的完整推理过程：

```json
{
  "question": "问题文本",
  "iterations": [
    {
      "iteration": 1,
      "plans": ["plan1", "plan2"],
      "verifications": [
        {
          "plan_index": 1,
          "original_plan": "...",
          "verdict": "supported",
          "corrected_plan": "...",
          "retrievals": 1
        }
      ],
      "updated_memory": "..."
    }
  ],
  "final_memory": "最终记忆内容",
  "final_answer": "最终答案",
  "total_retrievals": 3
}
```

### 2. 评估指标 (`metric_score.txt`)

```
EM: 0.xxx
F1: 0.xxx
ACC: 0.xxx
```

### 3. 配置备份 (`config.yaml`)

保存运行时使用的完整配置

## ⚙️ 配置参数说明

### RPVM核心参数

```yaml
rpvm_config:
  max_iter: 5                    # 最大迭代次数
  max_retrieval_attempts: 2      # 每个plan最大检索重试次数
  retrieval_topk: 5              # 每次检索返回文档数
  memory_max_tokens: 3000        # 记忆最大token数
  enable_memory_summary: True    # 启用记忆摘要
  planner_temperature: 0.7       # 规划器温度(较高=更有创造性)
  verifier_temperature: 0.3      # 验证器温度(较低=更保守)
  final_answer_temperature: 0.5  # 最终答案温度
```

### 数据集设置

```yaml
dataset_name: "hotpotqa"  # 或 "2wikimultihopqa"
split: ["test"]
```

### 检索器设置

```yaml
retrieval_method: "e5"
retrieval_topk: 5
retrieval_use_fp16: True
```

### 生成器设置

```yaml
framework: "openai"
generator_model: "gpt-3.5-turbo"
generation_params:
  max_tokens: 512
  temperature: 0.7
```

## 🔍 工作流程

以一个多跳问题为例：

**问题**: "What is the fight song of the university whose main campus is in Lawrence, Kansas?"

### 迭代1：规划与验证

**Planner生成计划**:
1. The university with main campus in Lawrence, Kansas is the University of Kansas
2. The fight song of the University of Kansas is "I'm a Jayhawk"

**Verifier验证**:
- Plan 1 → **supported** ✅ → 加入记忆
- Plan 2 → **contradicted** ❌ (实际是"Kansas Song") → 修正并加入记忆

**Memory更新**:
```
1. The university with main campus in Lawrence, Kansas is the University of Kansas. (verified)
2. The fight song of the University of Kansas is "Kansas Song". (corrected)
```

### 迭代2：生成答案

**Planner检查**: 记忆已足够 → 返回 "ANSWER_READY"

**最终答案**: "Kansas Song"

## 📈 性能优化建议

1. **调整迭代次数**: 根据问题复杂度调整 `max_iter`
2. **检索策略**: 调整 `retrieval_topk` 和 `max_retrieval_attempts`
3. **温度参数**: 
   - 规划器温度高 → 更多样化的计划
   - 验证器温度低 → 更保守的判断
4. **记忆管理**: 启用 `enable_memory_summary` 控制上下文长度
5. **批处理**: 调整 `generator_batch_size` 提高吞吐量

## 🐛 故障排查

### 问题1: OpenAI API错误

```
Error: Incorrect API key provided
```

**解决**: 检查API key是否正确设置

### 问题2: 检索器加载失败

```
Error: Cannot load index from path
```

**解决**: 
1. 确认 `index_path` 和 `corpus_path` 正确
2. 检查E5模型是否已下载
3. 参考FlashRAG文档构建索引

### 问题3: GPU内存不足

```
RuntimeError: CUDA out of memory
```

**解决**:
1. 设置 `gpu_id: null` 使用CPU
2. 减小 `retrieval_batch_size`
3. 设置 `retrieval_use_fp16: True`

### 问题4: 数据集加载失败

```
Error: Dataset not found
```

**解决**: 
1. 检查 `data_dir` 路径
2. 确认数据集已下载到FlashRAG数据目录
3. 参考FlashRAG文档准备数据集

## 📚 扩展阅读

- [PVM.md](PVM.md) - RPVM方法详细说明
- [需求文档.md](需求文档.md) - 完整实验需求
- [FlashRAG文档](../docs/) - FlashRAG框架文档

## 📝 引用

如果使用本实现，请引用：

```bibtex
@misc{rpvm2024,
  title={RPVM: Reflective Plan-Verify Memory for Multi-hop Question Answering},
  author={Your Name},
  year={2024}
}
```

## 🤝 贡献

欢迎提出问题和改进建议！

## 📄 许可

本项目遵循FlashRAG的许可协议。
