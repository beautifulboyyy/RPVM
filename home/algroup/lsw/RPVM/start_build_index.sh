#!/bin/bash

# 激活conda环境
source /home/algroup/anaconda3/bin/activate lsw_rpvm

# 设置GPU
export CUDA_VISIBLE_DEVICES=0,2

# 设置日志文件
LOG_FILE="/home/algroup/lsw/RPVM/build_index_$(date +%Y%m%d_%H%M%S).log"

# 运行索引构建（不使用--faiss_gpu以节省内存）
cd /home/algroup/lsw/RPVM

python -m flashrag.retriever.index_builder \
    --retrieval_method e5 \
    --model_path /home/algroup/lsw/RPVM/RPVM/e5-base-v2 \
    --corpus_path /home/algroup/lsw/RPVM/RPVM/indexes/wiki18_100w.jsonl \
    --save_dir /home/algroup/lsw/RPVM/RPVM/indexes/wiki18_100w_index/ \
    --use_fp16 \
    --max_length 256 \
    --batch_size 3072 \
    --pooling_method mean \
    --faiss_type IVF8192,Flat \
    > "$LOG_FILE" 2>&1

echo "索引构建完成，日志文件：$LOG_FILE"
