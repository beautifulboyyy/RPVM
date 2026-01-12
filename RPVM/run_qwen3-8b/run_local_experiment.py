"""
运行本地RPVM实验的脚本
使用 wiki18 小语料库 + qwen3-8b 本地模型
"""
import os
import sys
import argparse
from pathlib import Path

# 添加flashRAG路径（必须在导入RPVM之前添加）
script_dir = os.path.dirname(os.path.abspath(__file__))
# 当前脚本在 ~/lsw/RPVM/RPVM/run_qwen3-8b/
# 需要找到 ~/lsw/flashrag 目录
project_root = os.path.dirname(script_dir)  # ~/lsw/RPVM/RPVM

# 查找flashRAG目录：优先使用同级flashRAG，否则使用父目录的flashRAG
flashrag_path = None
for candidate in [script_dir, project_root]:
    flashrag_candidate = os.path.join(candidate, "flashrag")
    if os.path.exists(flashrag_candidate):
        flashrag_path = candidate
        break

# 如果当前目录结构没有flashrag，尝试project_parent
if not flashrag_path:
    project_parent = os.path.dirname(project_root)
    flashrag_candidate = os.path.join(project_parent, "flashrag")
    if os.path.exists(flashrag_candidate):
        flashrag_path = project_parent
        project_root = flashrag_candidate

if flashrag_path:
    sys.path.insert(0, flashrag_path)
    print(f"flashRAG路径: {flashrag_path}")
else:
    raise ImportError("无法找到flashRAG目录，请确保项目结构正确")

# 添加RPVM目录到路径（rpvm_pipeline.py 所在目录）
# script_dir 是 run_qwen3-8b，rpvm_pipeline.py 在 RPVM/ 目录下
rpvm_dir = os.path.dirname(script_dir)  # ~/lsw/RPVM/RPVM
sys.path.insert(0, rpvm_dir)

from flashrag.config import Config
from flashrag.utils import get_dataset
from rpvm_pipeline import RPVMPipeline


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

    # 修正路径为绝对路径（相对于RPVM目录）
    rpvm_root = os.path.dirname(os.path.abspath(__file__))

    if 'data_dir' in config and not os.path.isabs(config['data_dir']):
        config['data_dir'] = os.path.join(rpvm_root, config['data_dir'])
        print(f"数据集目录: {config['data_dir']}")

    if 'index_path' in config and not os.path.isabs(config['index_path']):
        config['index_path'] = os.path.join(rpvm_root, config['index_path'])
        print(f"索引路径: {config['index_path']}")

    if 'corpus_path' in config and not os.path.isabs(config['corpus_path']):
        config['corpus_path'] = os.path.join(rpvm_root, config['corpus_path'])
        print(f"语料库路径: {config['corpus_path']}")

    if 'save_dir' in config and not os.path.isabs(config['save_dir']):
        config['save_dir'] = os.path.join(rpvm_root, config['save_dir'])
        print(f"输出目录: {config['save_dir']}")

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
