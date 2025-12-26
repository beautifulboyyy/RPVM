"""
运行本地RPVM实验的脚本
使用 wiki18 小语料库 + qwen3-8b 本地模型
"""
import os
import sys
import argparse
from pathlib import Path

from RPVM.rpvm_pipeline import RPVMPipeline

# 添加flashRAG路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flashrag.config import Config
from flashrag.utils import get_dataset


def run_local_experiment(args):
    """运行本地RPVM实验"""
    
    # 设置保存标识
    save_note = f"rpvm_local_{args.split}"
    
    # 配置参数覆盖
    config_dict = {
        "split": [args.split],
        "gpu_id": args.gpu_id,
        "save_note": save_note,
    }
    
    # 加载配置
    config_file_path = os.path.join(os.path.dirname(__file__), "rpvm_local_config.yaml")
    config = Config(config_file_path=config_file_path, config_dict=config_dict)
    
    # 加载数据集
    print(f"加载数据集: {config['dataset_name']}, split: {args.split}")
    all_split = get_dataset(config)
    test_data = all_split[args.split]
    
    # 如果指定了样本数量(用于测试)
    if args.num_samples and args.num_samples > 0:
        print(f"仅使用 {args.num_samples} 个样本进行测试")
        # 使用 sample 方法而不是直接切片，保持 Dataset 对象类型
        from flashrag.dataset import Dataset
        sampled_data = test_data.data[:args.num_samples]
        test_data = Dataset(config, data=sampled_data)
    
    print(f"数据集大小: {len(test_data)}")
    
    # 创建RPVM Pipeline
    print("正在初始化 RPVM Pipeline...")
    pipeline = RPVMPipeline(config)
    
    # 运行实验
    print("开始运行 RPVM 实验...")
    result_dataset = pipeline.run(test_data, do_eval=True)
    
    print("实验完成！")
    print(f"结果保存到: {config['save_dir']}")
    
    return result_dataset


def main():
    parser = argparse.ArgumentParser(description="运行本地RPVM实验")
    
    parser.add_argument(
        "--split",
        type=str,
        default="dev",
        choices=["train", "dev", "test"],
        help="数据集分割"
    )
    
    parser.add_argument(
        "--gpu_id",
        type=str,
        default="0",
        help="GPU ID"
    )
    
    parser.add_argument(
        "--num_samples",
        type=int,
        default=5,
        help="测试样本数量，默认5个用于快速测试"
    )
    
    args = parser.parse_args()
    run_local_experiment(args)


if __name__ == "__main__":
    main()
