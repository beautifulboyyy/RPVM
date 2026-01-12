<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## Project Overview

FlashRAG is a Python toolkit for Retrieval Augmented Generation (RAG) research with 36 benchmark datasets and 23 state-of-the-art RAG algorithms. The repository includes a custom RPVM (Reflective Plan-Verify Memory) implementation for multi-hop question answering.

## Installation & Setup

```bash
# Basic installation
pip install -e .

# Full installation with all features
pip install flashrag-dev[full]

# Install specific components
pip install flashrag-dev[retriever]  # For retrievers (pyserini, sentence-transformers)
pip install flashrag-dev[generator]  # For generators (vllm)
pip install flashrag-dev[multimodal] # For multimodal RAG
```

## Common Commands

### Running Experiments

FlashRAG experiments use YAML config files and Python scripts:

```bash
# General FlashRAG experiments
cd examples/methods
python run_exp.py --dataset_name <dataset> --split test --gpu_id 0

# RPVM experiments (custom implementation in RPVM/)
cd RPVM
python run_rpvm_exp.py --dataset_name hotpotqa --split test --gpu_id 0
python run_rpvm_exp.py --dataset_name 2wikimultihopqa --split dev --gpu_id 0

# Small-scale testing
python run_rpvm_exp.py --dataset_name hotpotqa --split test --gpu_id 0 --num_samples 5

# Simple examples
python simple_example.py --mode simple  # Single question
python simple_example.py --mode batch   # Multiple questions
```

### Building Retrieval Indexes

```bash
# Build index using index_builder module
python -m flashrag.retriever.index_builder \
    --model_path <encoder_model_path> \
    --corpus_path <corpus.jsonl> \
    --index_path <output.index>
```

### Web UI

```bash
# Launch FlashRAG-UI (Gradio-based)
python webui/interface.py
```

### OpenAI API Configuration

Set API key via environment variable or .env file:
```bash
export OPENAI_API_KEY='your-api-key-here'
export OPENAI_BASE_URL='https://api.openai.com/v1'  # Optional
```

Or use command-line arguments:
```bash
python run_rpvm_exp.py --openai_api_key your-key --dataset_name hotpotqa
```

## Architecture

### Core Framework Structure

**flashrag/** - Main framework package
- `pipeline/` - RAG pipeline implementations (SequentialPipeline, BranchingPipeline, ActivePipeline, ReasoningPipeline, etc.)
- `retriever/` - Retrieval components (E5, BM25, DPR, Contriever, multimodal retrievers)
- `generator/` - Generation components (OpenAI, vLLM, HuggingFace, multimodal MLLMs)
- `refiner/` - Document refinement (LLMLingua compressor, selective context, KG refiner)
- `evaluator/` - Evaluation metrics (EM, F1, ACC)
- `dataset/` - Dataset loading and processing
- `prompt/` - Prompt templates
- `config/` - Configuration management
- `judger/` - Answer verification

### RPVM Custom Implementation

**RPVM/** - Custom RPVM method for multi-hop QA
- `rpvm_pipeline.py` - RPVMPipeline class extending BasicPipeline
- `rpvm_config.yaml` - RPVM-specific configuration
- `run_rpvm_exp.py` - Main experiment runner
- `simple_example.py` - Simple usage examples

**RPVM Workflow:**
1. **Planner** - Generates reasoning plans using LLM
2. **Retriever** - Retrieves documents for each plan (E5-based)
3. **Verifier** - Validates plans against retrieved docs (supported/contradicted/insufficient)
4. **Memory** - Stores verified/corrected plans across iterations
5. Iterates until answer ready or max iterations reached

### Pipeline Architecture

All pipelines inherit from `BasicPipeline` (flashrag/pipeline/pipeline.py:7):
- `run()` - Main inference process
- `evaluate()` - Post-generation evaluation

Key pipeline types:
- **SequentialPipeline** - Standard retrieve→generate flow
- **ReasoningPipeline** - Combines reasoning with retrieval
- **BranchingPipeline** - Multiple retrieval/generation branches
- **ActivePipeline** - Active learning-based retrieval

### Generator Abstraction

Supports multiple frameworks via unified interface:
- **OpenAI** - GPT models via API (framework: "openai")
- **vLLM** - Fast local inference (framework: "vllm")
- **HuggingFace** - Local models (framework: "hf")
- **Multimodal** - MLLMs like Llava, Qwen, InternVL

RPVM uses dual-mode generation (_call_generator in rpvm_pipeline.py:46):
- OpenAI: message list format
- Local HF: chat template format (Qwen-style)

### Configuration System

All experiments use YAML config files (flashrag/config/):
- Load via `Config(config_file_path, config_dict)` 
- Command-line args override config_dict values
- Key sections: dataset, retrieval, generation, evaluation, method-specific params

## Dataset Locations

- FlashRAG datasets: `datasets/` directory (configured via `data_dir`)
- RPVM datasets: `RPVM/datasets/`
- Document corpus: Configured via `corpus_path` (e.g., `indexes/domainrag_text_corpus.jsonl`)
- Indexes: `indexes/` or `RPVM/indexes/`

Supported datasets: HotpotQA, 2WikiMultihopQA, NQ, TriviaQA, WebQA, PopQA, and 30+ others.

## Key Configuration Parameters

### RPVM-Specific (rpvm_config section)
- `max_iter` - Maximum reasoning iterations (default: 5)
- `max_retrieval_attempts` - Retries per plan (default: 2)
- `retrieval_topk` - Documents per retrieval (default: 5)
- `memory_max_tokens` - Memory size limit (default: 3000)
- `enable_memory_summary` - Auto-summarize memory (default: true)
- `planner_temperature` - Plan generation temp (default: 0.7)
- `verifier_temperature` - Verification temp (default: 0.3)
- `final_answer_temperature` - Answer generation temp (default: 0.5)

### General FlashRAG
- `retrieval_method` - Retriever type (e5, bm25, dpr, etc.)
- `generator_model` - Model name or path
- `retrieval_topk` - Top-k documents
- `use_reranker` - Enable reranking
- `gpu_id` - GPU device ID(s)

## Important Notes

- **No standard test framework** - Tests exist but no unified pytest/unittest setup. Check individual test files (e.g., RPVM/test_rpvm.py)
- **OpenAI API required for RPVM** - Uses gpt-3.5-turbo by default
- **Index building is CPU-intensive** - Small corpus (~14K docs) takes ~1.5 hours on CPU
- **Environment variables** - RPVM reads OPENAI_API_KEY and OPENAI_BASE_URL from .env files
- **Ruff linting configured** - pyproject.toml extends select for W291, W293

## File Outputs

RPVM experiments save to `output/rpvm_experiments/`:
- `intermediate_data.jsonl` - Full reasoning trace per question
- `metric_score.txt` - EM/F1/ACC scores
- `config.yaml` - Saved configuration

FlashRAG experiments save based on `save_dir` config parameter.
