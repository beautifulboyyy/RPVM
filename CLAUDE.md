# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FlashRAG is a Python toolkit for Retrieval Augmented Generation (RAG) research. It includes 36 benchmark datasets and 23 RAG algorithms (including 7 reasoning-based methods). The repository also contains a custom RPVM (Reflective Plan-Verify Memory) implementation for multi-hop QA.

**Python:** >= 3.10

## Installation

```bash
# Basic installation
pip install -e .

# Full installation with all features
pip install flashrag-dev[full]

# Install specific components
pip install flashrag-dev[retriever]  # pyserini, sentence-transformers
pip install flashrag-dev[generator]  # vllm support
pip install flashrag-dev[multimodal] # multimodal RAG support
```

## Common Commands

### Running Experiments

```bash
# General FlashRAG experiments
cd examples/methods
python run_exp.py --dataset_name <dataset> --split test --gpu_id 0

# RPVM experiments (custom multi-hop QA implementation)
cd RPVM
python run_rpvm_exp.py --dataset_name hotpotqa --split test --gpu_id 0
python run_rpvm_exp.py --dataset_name 2wikimultihopqa --split dev --gpu_id 0

# Small-scale testing
python run_rpvm_exp.py --dataset_name hotpotqa --split test --gpu_id 0 --num_samples 5
```

### Building Retrieval Indexes

```bash
python -m flashrag.retriever.index_builder \
    --model_path <encoder_model_path> \
    --corpus_path <corpus.jsonl> \
    --index_path <output.index>
```

### Web UI

```bash
python webui/interface.py
```

### Linting

```bash
ruff check flashrag/ RPVM/
ruff check --fix flashrag/ RPVM/  # Auto-fix trailing whitespace
```

### Running Tests

```bash
# RPVM module tests
python RPVM/test_rpvm.py

# No unified pytest framework - individual test files exist
```

### Quick Example

```python
from flashrag.config import Config
from flashrag.utils import get_dataset
from flashrag.pipeline import SequentialPipeline

config = Config("my_config.yaml", config_dict={"gpu_id": 0, "dataset_name": "hotpotqa"})
dataset = get_dataset(config)["test"]
pipeline = SequentialPipeline(config)
result = pipeline.run(dataset)
```

### Key Entry Points

| File | Purpose |
|------|---------|
| `examples/methods/run_exp.py` | Run standard RAG experiments (naive, zero-shot, aar, etc.) |
| `RPVM/run_rpvm_exp.py` | Run RPVM multi-hop QA experiments |
| `examples/quick_start/demo_en.py` | Basic usage demo |
| `webui/interface.py` | Web UI launcher |

### Component Factory Functions

Use factory functions to load components:
- `get_retriever(config)` - Load retriever based on `retrieval_method`
- `get_generator(config)` - Load generator based on `framework`
- `get_refiner(config)` - Load refiner based on `refiner_name`
- `get_dataset(config)` - Load dataset from `data_dir`

### Configuration Pattern

All examples use `my_config.yaml` as a base config file with runtime overrides via `config_dict`:
- Base config: `my_config.yaml` in the same directory as the script
- Runtime overrides passed as dict: `Config("my_config.yaml", config_dict={"gpu_id": 0})`
- See `flashrag/config/basic_config.yaml` for all available options

## Architecture

### Core Framework (flashrag/)

| Module | Responsibility |
|--------|----------------|
| `pipeline/` | RAG workflow orchestration - SequentialPipeline, ReasoningPipeline, BranchingPipeline, ActivePipeline, IRCOTPipeline |
| `retriever/` | Dense (E5, BGE, Contriever), sparse (BM25), and multimodal retrieval |
| `generator/` | LLM generation via HF, vLLM, FastChat, or OpenAI API |
| `refiner/` | Document compression (LLMLingua, SelectiveContext, KG refiner) |
| `evaluator/` | EM, F1, ACC metrics |
| `dataset/` | Dataset and Item classes for data management |
| `config/` | YAML-based configuration system |

### Pipeline Base Class

All pipelines inherit from `BasicPipeline` (`flashrag/pipeline/pipeline.py:7`):
- `run(dataset)` - Main inference process
- `evaluate(dataset)` - Post-generation evaluation

### RPVM Custom Implementation (RPVM/)

A custom Reflective Plan-Verify Memory method for multi-hop QA:
1. **Planner** - Generates reasoning plans using LLM
2. **Retriever** - Retrieves documents for each plan (E5-based)
3. **Verifier** - Validates plans against retrieved docs
4. **Memory** - Stores verified/corrected plans across iterations

Key files:
- `rpvm_pipeline.py` - RPVMPipeline class extending BasicPipeline
- `run_rpvm_exp.py` - Experiment runner
- `simple_example.py` - Simple usage examples

### Configuration System

All experiments use YAML config files (`flashrag/config/config.py`):
- Load via `Config(config_file_path, config_dict)`
- Command-line args override config_dict values
- Key sections: dataset, retrieval, generation, evaluation, method-specific params

### Generator Abstraction

Supports multiple frameworks via unified interface:
- `"openai"` - OpenAI GPT models via API
- `"vllm"` - Fast local inference
- `"hf"` - HuggingFace local models
- `"multimodal"` - MLLMs like Llava, Qwen, InternVL

## Key Patterns

- **Factory pattern** for component loading (`get_retriever`, `get_generator`, etc.)
- **YAML-based configuration** with hierarchical merging
- **Dataset abstraction** with `Item`/`Dataset` classes supporting dynamic attributes

## Dataset Locations

- FlashRAG datasets: `datasets/` (configured via `data_dir`)
- RPVM datasets: `RPVM/datasets/`
- Document corpus: Configured via `corpus_path` parameter
- Indexes: `indexes/` or `RPVM/indexes/`

## Important Notes

- **No unified test framework** - Tests exist in individual files (e.g., `RPVM/test_rpvm.py`) but no pytest setup
- **OpenAI API required for RPVM** - Uses gpt-3.5-turbo by default; set `OPENAI_API_KEY` env var
- **Index building is CPU-intensive** - Small corpus (~14K docs) takes ~1.5 hours on CPU
- **Ruff linting** - pyproject.toml extends select for W291, W293 (trailing whitespace)

## RPVM-Specific Configuration

Key parameters in `rpvm_config` section:
- `max_iter` - Maximum reasoning iterations (default: 5)
- `max_retrieval_attempts` - Retries per plan (default: 2)
- `retrieval_topk` - Documents per retrieval (default: 5)
- `memory_max_tokens` - Memory size limit (default: 3000)
