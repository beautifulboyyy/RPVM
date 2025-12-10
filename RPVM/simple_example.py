"""
RPVM方法简单示例
演示如何使用RPVM Pipeline处理单个问题
"""
import os
import sys
from pathlib import Path

# 添加flashRAG路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flashrag.config import Config
from rpvm_pipeline import RPVMPipeline

# 加载.env文件
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已从 {env_path} 加载环境变量\n")
    else:
        print(f"⚠️  .env文件不存在: {env_path}\n")
except ImportError:
    print("提示: 安装python-dotenv可自动加载.env文件: pip install python-dotenv\n")


def simple_example():
    """简单示例：处理单个问题"""
    
    # 示例问题 (HotpotQA风格的多跳问题)
    example_question = "What is the name of the fight song of the university whose main campus is in Lawrence, Kansas?"
    
    print("=" * 80)
    print("RPVM方法简单示例")
    print("=" * 80)
    print(f"\n问题: {example_question}\n")
    
    # 加载配置
    config_file_path = os.path.join(os.path.dirname(__file__), "rpvm_config.yaml")
    
    # 可以通过config_dict覆盖配置
    config_dict = {
        "gpu_id": "0",
        "save_intermediate_data": True,
        "save_note": "rpvm_simple_example"
    }
    
    # 从环境变量读取OpenAI配置
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if openai_api_key:
        config_dict["openai_setting"] = {
            "api_key": openai_api_key,
            "base_url": openai_base_url
        }
        print(f"✅ 使用OpenAI配置: {openai_base_url}\n")
    else:
        print("⚠️  未找到OPENAI_API_KEY环境变量\n")
    
    try:
        config = Config(config_file_path=config_file_path, config_dict=config_dict)
    except Exception as e:
        print(f"配置加载失败: {e}")
        print("\n请确保:")
        print("1. rpvm_config.yaml中的路径设置正确")
        print("2. 已设置OPENAI_API_KEY环境变量")
        print("3. E5模型和索引文件已准备好")
        return
    
    # 创建Pipeline
    print("正在初始化RPVM Pipeline...")
    try:
        pipeline = RPVMPipeline(config)
    except Exception as e:
        print(f"Pipeline初始化失败: {e}")
        return
    
    # 运行单个问题
    print("开始推理...\n")
    result = pipeline._run_single_question(example_question)
    
    # 打印结果
    print("\n" + "=" * 80)
    print("推理过程:")
    print("=" * 80)
    
    for iter_info in result['iterations']:
        print(f"\n迭代 {iter_info['iteration']}:")
        print("-" * 40)
        
        if iter_info['plans'] == 'ANSWER_READY':
            print("状态: 记忆已足够，准备回答")
        else:
            print(f"计划数量: {len(iter_info['plans'])}")
            for i, plan in enumerate(iter_info['plans'], 1):
                print(f"  计划 {i}: {plan}")
            
            print("\n验证结果:")
            for ver in iter_info.get('verifications', []):
                print(f"  - Plan {ver['plan_index']}: {ver['verdict']}")
                if ver['verdict'] == 'contradicted':
                    print(f"    修正为: {ver['corrected_plan']}")
        
        if 'updated_memory' in iter_info:
            print(f"\n更新后的记忆:\n{iter_info['updated_memory']}")
    
    print("\n" + "=" * 80)
    print("最终结果:")
    print("=" * 80)
    print(f"\n答案: {result['final_answer']}")
    print(f"\n总检索次数: {result['total_retrievals']}")
    print(f"迭代次数: {len(result['iterations'])}")
    
    print("\n" + "=" * 80)


def batch_example():
    """批量示例：处理多个问题"""
    
    # 示例问题集
    questions = [
        "What is the name of the fight song of the university whose main campus is in Lawrence, Kansas?",
        "In what city was the creator of Sherlock Holmes born?",
        "What is the capital of the country where the Eiffel Tower is located?"
    ]
    
    print("=" * 80)
    print("RPVM方法批量示例")
    print("=" * 80)
    
    # 加载配置
    config_file_path = os.path.join(os.path.dirname(__file__), "rpvm_config.yaml")
    config_dict = {
        "gpu_id": "0",
        "save_intermediate_data": True,
        "save_note": "rpvm_batch_example"
    }
    
    # 从环境变量读取OpenAI配置
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if openai_api_key:
        config_dict["openai_setting"] = {
            "api_key": openai_api_key,
            "base_url": openai_base_url
        }
    
    try:
        config = Config(config_file_path=config_file_path, config_dict=config_dict)
        pipeline = RPVMPipeline(config)
    except Exception as e:
        print(f"初始化失败: {e}")
        return
    
    # 处理每个问题
    for i, question in enumerate(questions, 1):
        print(f"\n问题 {i}/{len(questions)}: {question}")
        print("-" * 80)
        
        result = pipeline._run_single_question(question)
        print(f"答案: {result['final_answer']}")
        print(f"迭代: {len(result['iterations'])}次, 检索: {result['total_retrievals']}次")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="RPVM简单示例")
    parser.add_argument(
        "--mode",
        type=str,
        default="simple",
        choices=["simple", "batch"],
        help="运行模式: simple(单个问题) 或 batch(多个问题)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "simple":
        simple_example()
    else:
        batch_example()
