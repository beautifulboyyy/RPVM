"""
设置本地实验环境的脚本
1. 从 wiki18_100w.jsonl 提取小语料库
2. 构建 e5 索引
3. 筛选部分 2wikimultihopqa 数据
"""
import os
import sys
import json
import random
from pathlib import Path

# 添加flashRAG路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def extract_small_corpus(input_path, output_path, num_samples=1000, seed=2024):
    """从大语料库提取小语料库"""
    print(f"从 {input_path} 提取 {num_samples} 条数据...")
    
    # 先统计总行数
    print("统计总行数...")
    total_lines = 0
    with open(input_path, 'r', encoding='utf-8') as f:
        for _ in f:
            total_lines += 1
    print(f"总共 {total_lines} 条数据")
    
    # 随机选择行号
    random.seed(seed)
    if num_samples >= total_lines:
        selected_indices = set(range(total_lines))
    else:
        selected_indices = set(random.sample(range(total_lines), num_samples))
    
    # 提取选中的行
    print("提取数据...")
    extracted_data = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f):
            if idx in selected_indices:
                data = json.loads(line.strip())
                # 重新分配 ID
                data['id'] = len(extracted_data)
                extracted_data.append(data)
                if len(extracted_data) % 100 == 0:
                    print(f"已提取 {len(extracted_data)} 条")
    
    # 保存
    print(f"保存到 {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for data in extracted_data:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    
    print(f"完成！共提取 {len(extracted_data)} 条数据")
    return len(extracted_data)


def extract_small_dataset(input_path, output_path, num_samples=50, seed=2024):
    """从数据集提取小样本"""
    print(f"从 {input_path} 提取 {num_samples} 条数据...")
    
    data_list = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            data_list.append(json.loads(line.strip()))
    
    print(f"总共 {len(data_list)} 条数据")
    
    random.seed(seed)
    if num_samples >= len(data_list):
        selected_data = data_list
    else:
        selected_data = random.sample(data_list, num_samples)
    
    # 保存
    print(f"保存到 {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for data in selected_data:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    
    print(f"完成！共提取 {len(selected_data)} 条数据")
    return len(selected_data)


def build_index(corpus_path, model_path, save_dir, batch_size=32):
    """构建 e5 索引"""
    from flashrag.retriever.index_builder import Index_Builder
    
    print(f"构建索引...")
    print(f"  语料库: {corpus_path}")
    print(f"  模型: {model_path}")
    print(f"  保存目录: {save_dir}")
    
    index_builder = Index_Builder(
        retrieval_method="e5",
        model_path=model_path,
        corpus_path=corpus_path,
        save_dir=save_dir,
        max_length=512,
        batch_size=batch_size,
        use_fp16=True,
        faiss_type="Flat",
    )
    index_builder.build_index()
    print("索引构建完成！")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="设置本地实验环境")
    parser.add_argument("--wiki_corpus_path", type=str, required=True,
                        help="wiki18_100w.jsonl 的路径")
    parser.add_argument("--e5_model_path", type=str, required=True,
                        help="e5-base-v2 模型的路径")
    parser.add_argument("--output_dir", type=str, default=".",
                        help="输出目录")
    parser.add_argument("--corpus_samples", type=int, default=1000,
                        help="语料库样本数量")
    parser.add_argument("--dataset_samples", type=int, default=20,
                        help="测试数据集样本数量")
    parser.add_argument("--batch_size", type=int, default=32,
                        help="索引构建批次大小")
    parser.add_argument("--skip_corpus", action="store_true",
                        help="跳过语料库提取")
    parser.add_argument("--skip_index", action="store_true",
                        help="跳过索引构建")
    parser.add_argument("--skip_dataset", action="store_true",
                        help="跳过数据集提取")
    
    args = parser.parse_args()
    
    # 设置路径
    output_dir = Path(args.output_dir)
    small_corpus_path = output_dir / "indexes" / "wiki18_small_corpus.jsonl"
    small_index_dir = output_dir / "indexes" / "wiki18_small_index"
    small_dataset_path = output_dir / "datasets" / "2wikimultihopqa" / "dev_small.jsonl"
    dataset_input_path = output_dir / "datasets" / "2wikimultihopqa" / "dev.jsonl"
    
    # 1. 提取小语料库
    if not args.skip_corpus:
        extract_small_corpus(
            args.wiki_corpus_path,
            str(small_corpus_path),
            num_samples=args.corpus_samples
        )
    
    # 2. 构建索引
    if not args.skip_index:
        build_index(
            str(small_corpus_path),
            args.e5_model_path,
            str(small_index_dir),
            batch_size=args.batch_size
        )
    
    # 3. 提取小数据集
    if not args.skip_dataset:
        extract_small_dataset(
            str(dataset_input_path),
            str(small_dataset_path),
            num_samples=args.dataset_samples
        )
    
    print("\n" + "=" * 60)
    print("设置完成！生成的文件：")
    print(f"  小语料库: {small_corpus_path}")
    print(f"  索引目录: {small_index_dir}")
    print(f"  索引文件: {small_index_dir / 'e5_Flat.index'}")
    print(f"  小数据集: {small_dataset_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
