#!/bin/bash

# 1. 激活环境
source /home/algroup/anaconda3/bin/activate lsw_rpvm

# 2. 设置显卡
export CUDA_VISIBLE_DEVICES=0

# 3. 设置日志名
LOG_FILE="/home/algroup/lsw/RPVM/build_index_sq8_$(date +%Y%m%d_%H%M%S).log"

# 4. 执行构建 (关键修改：--faiss_type SQ8)
cd /home/algroup/lsw/RPVM

nohup python -m flashrag.retriever.index_builder \
    --retrieval_method e5 \
    --model_path /home/algroup/lsw/RPVM/RPVM/e5-base-v2 \
    --corpus_path /home/algroup/lsw/RPVM/RPVM/indexes/wiki18_100w.jsonl \
    --save_dir /home/algroup/lsw/RPVM/RPVM/indexes/wiki18_100w_index_sq8/ \
    --use_fp16 \
    --max_length 512 \
    --batch_size 512 \
    --pooling_method mean \
    --faiss_type SQ8 \
    > "$LOG_FILE" 2>&1 &