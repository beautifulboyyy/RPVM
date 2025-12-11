# RPVM 快速入门指南 ⚡

> 5分钟快速上手RPVM方法

## 🎯 第一步：环境检查

```bash
# 1. 激活flashRAG环境
conda activate flashRAG  # 或你的环境名

# 2. 安装依赖
pip install openai tiktoken

# 3. 进入RPVM目录
cd RPVM

# 4. 运行测试
python test_rpvm.py
```

**期望输出**: `🎉 所有测试通过！`

---

## 🔑 第二步：配置API密钥

```bash
# Windows PowerShell
$env:OPENAI_API_KEY='sk-your-api-key-here'

# Linux/Mac
export OPENAI_API_KEY='sk-your-api-key-here'
```

**验证**: `echo $env:OPENAI_API_KEY` (PowerShell) 或 `echo $OPENAI_API_KEY` (Linux/Mac)

---

## ⚙️ 第三步：配置路径

编辑 `rpvm_config.yaml`：

```yaml
# 必须修改的路径
data_dir: "你的数据集目录"                    # 例如: "D:/flashRAG/datasets"
retrieval_model_path: "你的E5模型路径"        # 例如: "D:/models/e5-base-v2"
index_path: "你的索引文件路径"                # 例如: "D:/flashRAG/indexes/e5_Flat.index"
corpus_path: "你的语料库路径"                 # 例如: "D:/flashRAG/indexes/general_knowledge.jsonl"
```

💡 **找不到这些文件？** 参考 [使用指南.md](使用指南.md) 的数据准备部分

---

## 🧪 第四步：测试运行

### 选项A：简单示例（推荐新手）

```bash
python simple_example.py --mode simple
```

这会处理一个示例问题并展示完整推理过程。

### 选项B：小规模实验

```bash
python run_rpvm_exp.py \
    --dataset_name hotpotqa \
    --split test \
    --num_samples 5 \
    --gpu_id 0
```

这会在5个样本上运行完整流程。

---

## 📊 第五步：查看结果

```bash
# 查看输出目录
ls output/rpvm_experiments/

# 查看评估指标
cat output/rpvm_experiments/metric_score.txt

# 查看中间数据（前3行）
head -3 output/rpvm_experiments/intermediate_data.jsonl
```

---

## 🚀 第六步：运行完整实验

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

⏱️ **预计时间**: 
- HotpotQA (~7,400样本): 2-4小时
- 2WikiMultihopQA (~12,500样本): 3-6小时

---

## ❓ 常见问题速查

### Q: 提示 "OpenAI API key not found"
```bash
# 重新设置环境变量
$env:OPENAI_API_KEY='你的密钥'
```

### Q: 提示 "Cannot load index"
```yaml
# 检查rpvm_config.yaml中的路径是否正确
index_path: "正确的路径"
corpus_path: "正确的路径"
```

### Q: GPU内存不足
```bash
# 使用CPU运行
python run_rpvm_exp.py --dataset_name hotpotqa --split test --gpu_id null
```

### Q: 想要更详细的输出
```python
# 在rpvm_config.yaml中设置
save_intermediate_data: True
```

---

## 📚 下一步学习

1. ✅ **已完成**: 基本运行
2. 📖 **阅读**: [README.md](README.md) - 了解方法原理
3. 🔧 **调优**: [使用指南.md](使用指南.md) - 参数调优
4. 📊 **分析**: 查看中间数据，理解推理过程
5. 🎯 **优化**: 根据结果调整配置

---

## 🎁 快速参考

### 目录结构
```
RPVM/
├── rpvm_config.yaml      # ← 配置文件（需修改路径）
├── rpvm_pipeline.py      # 核心实现
├── run_rpvm_exp.py       # ← 运行实验
├── simple_example.py     # ← 简单示例
├── test_rpvm.py          # ← 测试脚本
├── README.md             # 完整文档
├── 使用指南.md           # 详细指南
└── output/               # 输出目录（自动创建）
```

### 命令速查

| 操作 | 命令 |
|------|------|
| 测试环境 | `python test_rpvm.py` |
| 简单示例 | `python simple_example.py` |
| 小规模测试 | `python run_rpvm_exp.py --num_samples 5 ...` |
| 完整实验 | `python run_rpvm_exp.py --dataset_name hotpotqa ...` |
| 查看帮助 | `python run_rpvm_exp.py --help` |

### 配置速查

| 参数 | 位置 | 说明 |
|------|------|------|
| API密钥 | 环境变量 | `OPENAI_API_KEY` |
| 数据路径 | `rpvm_config.yaml` | `data_dir` |
| 模型路径 | `rpvm_config.yaml` | `retrieval_model_path` |
| 迭代次数 | `rpvm_config.yaml` | `rpvm_config.max_iter` |
| GPU设置 | 命令行/配置 | `--gpu_id 0` 或 `gpu_id: "0"` |

---

## 💡 专业提示

1. **首次运行**: 一定要先用 `--num_samples 5` 测试
2. **监控成本**: OpenAI API按token计费，注意使用量
3. **保存配置**: 每次实验保存一份配置文件副本
4. **分析日志**: 检查中间数据了解推理过程
5. **迭代优化**: 根据结果调整参数，重复实验

---

## 🆘 需要帮助？

1. 📖 查看 [README.md](README.md)
2. 📚 查看 [使用指南.md](使用指南.md)
3. 🔍 查看 [实现总结.md](实现总结.md)
4. 🐛 运行 `python test_rpvm.py` 诊断问题

---

**祝实验顺利！** 🎉
