"""
运行RPVM实验的主文件
支持HotpotQA和2WikiMultihopQA数据集

使用方法:
python run_rpvm_exp.py --dataset_name hotpotqa --split test --gpu_id 0
python run_rpvm_exp.py --dataset_name 2wikimultihopqa --split test --gpu_id 0

示例运行(小样本测试):
python run_rpvm_exp.py --dataset_name hotpotqa --split test --gpu_id 0 --num_samples 5
"""
import os
import sys
import argparse
from pathlib import Path

# 添加flashRAG路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flashrag.config import Config
from flashrag.utils import get_dataset
from rpvm_pipeline import RPVMPipeline

# 加载.env文件
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"已从 {env_path} 加载环境变量")
except ImportError:
    print("提示: 安装python-dotenv可自动加载.env文件: pip install python-dotenv")


def run_rpvm_experiment(args):
    """运行RPVM实验"""
    
    # 设置保存标识
    save_note = f"rpvm_{args.dataset_name}_{args.split}"
    
    # 配置参数覆盖
    config_dict = {
        "dataset_name": args.dataset_name,
        "split": args.split,
        "gpu_id": args.gpu_id,
        "save_note": save_note,
    }
    
    # 如果指定了OpenAI API Key
    if args.openai_api_key:
        config_dict["openai_setting"] = {
            "api_key": args.openai_api_key,
            "base_url": args.openai_base_url or "https://api.openai.com/v1"
        }
    else:
        # 从环境变量读取
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if openai_api_key:
            config_dict["openai_setting"] = {
                "api_key": openai_api_key,
                "base_url": openai_base_url
            }
            print(f"使用环境变量中的OpenAI配置: {openai_base_url}")
    
    # 加载配置
    config_file_path = os.path.join(os.path.dirname(__file__), "rpvm_config.yaml")
    config = Config(config_file_path=config_file_path, config_dict=config_dict)
    
    # 加载数据集
    print(f"Loading datasets: {args.dataset_name}, split: {args.split}")
    all_split = get_dataset(config)
    test_data = all_split[args.split]
    
    # 如果指定了样本数量(用于测试)
    if args.num_samples and args.num_samples > 0:
        print(f"Using only {args.num_samples} samples for testing")
        test_data = test_data[:args.num_samples]
    
    print(f"Dataset size: {len(test_data)}")
    
    # 创建RPVM Pipeline
    print("Initializing RPVM Pipeline...")
    pipeline = RPVMPipeline(config)
    
    # 运行实验
    print("Running RPVM experiment...")
    result_dataset = pipeline.run(test_data, do_eval=True)
    
    print("Experiment completed!")
    print(f"Results saved to: {config['save_dir']}")
    
    return result_dataset


def main():
    parser = argparse.ArgumentParser(description="Run RPVM experiment on multi-hop QA datasets")
    
    # 必需参数
    parser.add_argument(
        "--dataset_name",
        type=str,
        required=True,
        choices=["hotpotqa", "2wikimultihopqa"],
        help="Dataset to use for the experiment"
    )
    
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        choices=["train", "dev", "test"],
        help="Dataset split to use"
    )
    
    parser.add_argument(
        "--gpu_id",
        type=str,
        default="0",
        help="GPU ID to use (e.g., '0' or '0,1')"
    )
    
    # 可选参数
    parser.add_argument(
        "--num_samples",
        type=int,
        default=None,
        help="Number of samples to process (for testing). If not specified, use all samples."
    )
    
    parser.add_argument(
        "--openai_api_key",
        type=str,
        default=None,
        help="OpenAI API key. If not specified, will read from environment variable OPENAI_API_KEY"
    )
    
    parser.add_argument(
        "--openai_base_url",
        type=str,
        default=None,
        help="OpenAI API base URL. If not specified, will read from environment variable OPENAI_BASE_URL"
    )
    
    args = parser.parse_args()
    
    # 检查OpenAI API Key
    if not args.openai_api_key and not os.getenv("OPENAI_API_KEY"):
        print("WARNING: OpenAI API key not found!")
        print("Please either:")
        print("  1. Set environment variable: export OPENAI_API_KEY='your-key'")
        print("  2. Use .env file in project root with OPENAI_API_KEY='your-key'")
        print("  3. Pass via argument: --openai_api_key your-key")
        sys.exit(1)
    
    # 运行实验
    run_rpvm_experiment(args)


if __name__ == "__main__":
    main()
