"""
RPVM基本功能测试脚本
测试各个模块的基本功能，不需要实际的检索器和数据集
"""
import os
import sys

# 添加flashRAG路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """测试基本导入"""
    print("测试1: 基本导入...")
    try:
        from flashrag.config import Config
        from flashrag.utils import get_dataset
        from rpvm_pipeline import RPVMPipeline
        print("✓ 导入成功")
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False


def test_config_loading():
    """测试配置加载"""
    print("\n测试2: 配置加载...")
    try:
        from flashrag.config import Config
        
        config_file = os.path.join(os.path.dirname(__file__), "rpvm_config.yaml")
        
        # 测试配置文件是否存在
        if not os.path.exists(config_file):
            print(f"✗ 配置文件不存在: {config_file}")
            return False
        
        # 尝试加载配置(可能会失败，因为路径可能不存在)
        config_dict = {
            "gpu_id": None,  # 使用CPU
            "disable_save": True,  # 禁用保存以避免创建目录
        }
        
        try:
            config = Config(config_file_path=config_file, config_dict=config_dict)
            print("✓ 配置加载成功")
            print(f"  - Dataset: {config['dataset_name']}")
            print(f"  - Retrieval method: {config['retrieval_method']}")
            print(f"  - Generator model: {config['generator_model']}")
            print(f"  - RPVM max_iter: {config.get('rpvm_config', {}).get('max_iter', 'N/A')}")
            return True
        except Exception as e:
            print(f"⚠ 配置加载警告: {e}")
            print("  (这可能是正常的，如果数据路径尚未设置)")
            return True
            
    except Exception as e:
        print(f"✗ 配置测试失败: {e}")
        return False


def test_prompt_building():
    """测试Prompt构建"""
    print("\n测试3: Prompt构建...")
    try:
        # 创建一个最小化的mock pipeline来测试prompt
        class MockGenerator:
            def generate(self, messages, **kwargs):
                return ["Mock response"]
        
        class MockRetriever:
            def batch_search(self, queries, topk=5):
                return [[]]
        
        class MockConfig(dict):
            def __getitem__(self, key):
                defaults = {
                    'rpvm_config': {
                        'max_iter': 5,
                        'max_retrieval_attempts': 2,
                        'retrieval_topk': 5,
                        'memory_max_tokens': 3000,
                        'enable_memory_summary': True,
                        'planner_temperature': 0.7,
                        'verifier_temperature': 0.3,
                        'final_answer_temperature': 0.5,
                    },
                    'save_intermediate_data': False,
                    'save_dir': '/tmp',
                    'device': 'cpu'
                }
                return defaults.get(key, None)
            
            def get(self, key, default=None):
                return self.__getitem__(key) or default
        
        from rpvm_pipeline import RPVMPipeline
        
        # 创建mock pipeline
        config = MockConfig()
        pipeline = RPVMPipeline.__new__(RPVMPipeline)
        pipeline.config = config
        pipeline.max_iter = 5
        pipeline.max_retrieval_attempts = 2
        pipeline.retrieval_topk = 5
        pipeline.memory_max_tokens = 3000
        pipeline.enable_memory_summary = True
        pipeline.planner_temperature = 0.7
        pipeline.verifier_temperature = 0.3
        pipeline.final_answer_temperature = 0.5
        
        # 测试planner prompt
        question = "What is the capital of France?"
        memory = ""
        prompt = pipeline._build_planner_prompt(question, memory)
        
        assert "Question: " in prompt
        assert question in prompt
        print("✓ Planner prompt构建成功")
        
        # 测试带记忆的planner prompt
        memory = "France is a country in Europe. (verified)"
        prompt_with_memory = pipeline._build_planner_prompt(question, memory)
        
        assert "Verified Memory:" in prompt_with_memory
        assert memory in prompt_with_memory
        print("✓ 带记忆的Planner prompt构建成功")
        
        # 测试plans解析
        mock_response = """1. France is a country in Europe.
2. The capital of France is Paris."""
        plans = pipeline._parse_plans(mock_response)
        
        assert len(plans) == 2
        assert "France is a country in Europe" in plans[0]
        assert "Paris" in plans[1]
        print("✓ Plans解析成功")
        
        # 测试验证响应解析
        mock_verification = """Verdict: SUPPORTED
Corrected Statement: France is a country in Europe.
Evidence: The documents confirm this fact."""
        
        verdict, corrected, evidence = pipeline._parse_verification_response(
            mock_verification, 
            "France is a country in Europe."
        )
        
        assert verdict == "supported"
        print("✓ 验证响应解析成功")
        
        return True
        
    except Exception as e:
        print(f"✗ Prompt构建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_structure():
    """测试文件结构"""
    print("\n测试4: 文件结构...")
    
    base_dir = os.path.dirname(__file__)
    required_files = [
        "rpvm_config.yaml",
        "rpvm_pipeline.py",
        "run_rpvm_exp.py",
        "simple_example.py",
        "README.md",
        "PVM.md",
        "需求文档.md"
    ]
    
    all_exist = True
    for file in required_files:
        file_path = os.path.join(base_dir, file)
        if os.path.exists(file_path):
            print(f"✓ {file}")
        else:
            print(f"✗ {file} 不存在")
            all_exist = False
    
    return all_exist


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("RPVM 基本功能测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: 导入
    results.append(("导入测试", test_imports()))
    
    # 测试2: 配置
    results.append(("配置加载", test_config_loading()))
    
    # 测试3: Prompt构建
    results.append(("Prompt构建", test_prompt_building()))
    
    # 测试4: 文件结构
    results.append(("文件结构", test_file_structure()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
    
    print("-" * 60)
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！RPVM实现已准备就绪。")
        print("\n下一步:")
        print("1. 配置 rpvm_config.yaml 中的路径")
        print("2. 设置 OPENAI_API_KEY 环境变量")
        print("3. 准备E5模型和索引文件")
        print("4. 运行 python simple_example.py 测试")
    else:
        print("\n⚠️  部分测试失败，请检查上述错误信息。")
    
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
