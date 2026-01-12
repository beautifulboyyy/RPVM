"""
RPVM Pipeline Implementation
Reflective Plan-Verify Memory for Multi-hop QA

Based on FlashRAG framework implement RPVM method
"""
import json
import re
from typing import List, Dict, Tuple, Optional
from tqdm import tqdm
from flashrag.pipeline import BasicPipeline
from flashrag.utils import get_retriever, get_generator
from flashrag.prompt import PromptTemplate
from prompt_loader import PromptLoader


class RPVMPipeline(BasicPipeline):
    """
    RPVM Pipeline: Reflective Plan-Verify Memory
    核心流程: 反思规划 -> 检索验证 -> 记忆更新 -> 迭代
    """

    def __init__(self, config, prompt_template=None):
        super().__init__(config, prompt_template)
        
        # 初始化检索器和生成器
        self.retriever = get_retriever(config)
        self.generator = get_generator(config)
        
        # 判断是否使用OpenAI框架
        self.use_openai = config['framework'] == 'openai' if 'framework' in config else False
        
        # RPVM特定配置
        rpvm_config = config['rpvm_config'] if 'rpvm_config' in config else {}
        self.max_iter = rpvm_config.get('max_iter', 5) if isinstance(rpvm_config, dict) else 5
        self.max_retrieval_attempts = rpvm_config.get('max_retrieval_attempts', 2) if isinstance(rpvm_config, dict) else 2
        self.retrieval_topk = rpvm_config.get('retrieval_topk', 5) if isinstance(rpvm_config, dict) else 5
        self.memory_max_tokens = rpvm_config.get('memory_max_tokens', 3000) if isinstance(rpvm_config, dict) else 3000
        self.enable_memory_summary = rpvm_config.get('enable_memory_summary', True) if isinstance(rpvm_config, dict) else True
        self.planner_temperature = rpvm_config.get('planner_temperature', 0.7) if isinstance(rpvm_config, dict) else 0.7
        self.verifier_temperature = rpvm_config.get('verifier_temperature', 0.3) if isinstance(rpvm_config, dict) else 0.3
        self.final_answer_temperature = rpvm_config.get('final_answer_temperature', 0.5) if isinstance(rpvm_config, dict) else 0.5
        
        # 初始化Prompt Loader
        prompt_dir = rpvm_config.get('prompt_dir', 'openai') if isinstance(rpvm_config, dict) else 'openai'
        self.prompt_loader = PromptLoader(prompts_dir=prompt_dir)

        # 检测是否是Qwen3模型（需要禁用thinking模式）
        self.is_qwen3 = False
        if hasattr(self.generator, 'model_name'):
            self.is_qwen3 = 'qwen3' in self.generator.model_name.lower()

        # 用于记录中间数据
        self.intermediate_data = []

    def _call_generator(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> str:
        """
        统一的生成器调用接口，支持 OpenAI 和本地 HF 模型
        """
        if self.use_openai:
            # OpenAI 格式：消息列表
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = self.generator.generate(
                [messages],
                temperature=temperature,
                max_tokens=max_tokens
            )[0]
        else:
            # 本地 HF 模型
            if self.is_qwen3 and hasattr(self.generator, 'tokenizer'):
                # Qwen3: 使用 apply_chat_template 并禁用 thinking 模式
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                # 使用 enable_thinking=True 打开思考模式
                text = self.generator.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=True  # 打开思考模式以提升推理能力
                )
                response = self.generator.generate(
                    [text],
                    temperature=temperature,
                    max_new_tokens=max_tokens
                )[0]
            else:
                # 其他 HF 模型：使用手动构建的 chat template
                full_prompt = f"""<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{user_prompt}<|im_end|>
<|im_start|>assistant
"""
                response = self.generator.generate(
                    [full_prompt],
                    temperature=temperature,
                    max_new_tokens=max_tokens
                )[0]

        return response.strip()

    def run(self, dataset, do_eval=True, pred_process_fun=None):
        """
        对整个数据集运行RPVM pipeline
        """
        pred_answer_list = []
        
        for item in tqdm(dataset, desc="RPVM Processing"):
            question = item.question
            
            # 运行RPVM单个样本
            result = self._run_single_question(question)
            
            pred_answer_list.append(result['final_answer'])
            
            # 保存中间数据
            if self.config['save_intermediate_data']:
                self.intermediate_data.append({
                    'question': question,
                    'iterations': result['iterations'],
                    'final_memory': result['final_memory'],
                    'final_answer': result['final_answer'],
                    'total_retrievals': result['total_retrievals']
                })
        
        # 更新数据集的预测结果
        dataset.update_output("pred", pred_answer_list)
        
        # 保存中间数据到文件
        if self.config['save_intermediate_data']:
            self._save_intermediate_data()
        
        # 评估
        dataset = self.evaluate(dataset, do_eval=do_eval, pred_process_fun=pred_process_fun)
        
        return dataset

    def _run_single_question(self, question: str) -> Dict:
        """
        对单个问题运行RPVM流程
        
        Returns:
            包含最终答案、记忆、迭代历史等信息的字典
        """
        memory = ""
        iterations = []
        total_retrievals = 0
        
        for iter_idx in range(self.max_iter):
            # Step 1: Reflective Planner - 生成计划链
            plans = self._planner(question, memory)
            
            # 检查是否准备好回答
            if plans == "ANSWER_READY":
                final_answer = self._generate_final_answer(question, memory)
                iterations.append({
                    'iteration': iter_idx + 1,
                    'plans': 'ANSWER_READY',
                    'memory_update': 'Ready to answer',
                    'final_answer': final_answer
                })
                break
            
            # 记录本轮迭代信息
            iter_info = {
                'iteration': iter_idx + 1,
                'plans': plans,
                'verifications': []
            }
            
            # Step 2 & 3: 对每个plan进行验证和记忆更新
            should_break = False
            for plan_idx, plan in enumerate(plans):
                # 验证当前plan
                verdict, corrected_plan, evidence, retrievals = self._verify_plan(
                    plan, question, memory
                )
                total_retrievals += retrievals
                
                verification_info = {
                    'plan_index': plan_idx + 1,
                    'original_plan': plan,
                    'verdict': verdict,
                    'corrected_plan': corrected_plan,
                    'retrievals': retrievals
                }
                iter_info['verifications'].append(verification_info)
                
                # 根据验证结果更新记忆
                if verdict == "supported":
                    memory += f"\n{corrected_plan} (verified)"
                elif verdict == "contradicted":
                    memory += f"\n{corrected_plan} (corrected)"
                    should_break = True  # 短路当前轮
                    break
                # insufficient情况不更新记忆
            
            # 检查记忆长度，必要时进行摘要
            if self.enable_memory_summary:
                memory = self._check_and_summarize_memory(memory)
            
            iter_info['updated_memory'] = memory
            iterations.append(iter_info)
            
            # 如果遇到contradicted，短路当前轮
            if should_break:
                continue
        
        # 如果达到最大迭代次数，仍生成最佳答案
        if iter_idx == self.max_iter - 1 and plans != "ANSWER_READY":
            final_answer = self._generate_best_effort_answer(question, memory)
        else:
            if plans != "ANSWER_READY":
                final_answer = self._generate_best_effort_answer(question, memory)
        
        return {
            'final_answer': final_answer,
            'final_memory': memory,
            'iterations': iterations,
            'total_retrievals': total_retrievals
        }

    def _planner(self, question: str, memory: str) -> any:
        """
        Reflective Planner: 基于问题和当前记忆生成推理计划链（假设生成模式）

        Returns:
            "ANSWER_READY" 或 计划列表 [plan1, plan2, ...]
        """
        system_prompt, user_prompt = self.prompt_loader.get_planner_prompt(question, memory)

        max_retries = 2
        for retry in range(max_retries):
            response = self._call_generator(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=self.planner_temperature,
                max_tokens=512
            )

            response = response.strip()
            if "ANSWER_READY" in response:
                return "ANSWER_READY"

            plans = self._parse_plans(response)

            # 检查是否解析到有效plan
            valid_plans = [p for p in plans if p and not p.startswith("Unable to parse")]
            if valid_plans:
                return valid_plans

            # 如果解析失败且还有重试机会，重新生成
            if retry < max_retries - 1:
                print(f"Planner解析失败，重试 {retry + 1}/{max_retries}")
                continue

        # 所有重试都失败，返回一个简单的fallback plan
        print(f"Planner多次解析失败，使用fallback plan")
        return [f"Find information to answer: {question}"]

    def _parse_plans(self, response: str) -> List[str]:
        """从LLM响应中解析计划列表，支持多种格式"""
        plans = []
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            # 跳过空行和无关内容
            if not line or line.startswith('#') or line.startswith('['):
                continue
            
            # 匹配 "plan1: xxx" 格式（推荐格式）
            match = re.match(r'^plan\d+[:\s]+(.+)$', line, re.IGNORECASE)
            if match:
                plan_text = match.group(1).strip()
                if plan_text:
                    plans.append(plan_text)
                continue
            
            # 匹配 "1. xxx" 或 "1) xxx" 格式
            match = re.match(r'^(\d+)[\.\)\s]+(.+)$', line)
            if match:
                plan_text = match.group(2).strip()
                if plan_text:
                    plans.append(plan_text)
                continue
            
            # 匹配以 "- " 开头的列表格式
            match = re.match(r'^-\s+(.+)$', line)
            if match:
                plan_text = match.group(1).strip()
                if plan_text:
                    plans.append(plan_text)
        
        # 如果没有解析到计划，尝试直接按行分割（过滤掉明显无效的行）
        if not plans and response.strip():
            for line in lines:
                line = line.strip()
                # 过滤掉思考标签和命令式语句
                if line and not line.startswith('#') and not line.startswith('[') and not line.startswith('<'):
                    # 过滤掉以命令动词开头的行
                    if not re.match(r'^(Find|Search|Check|Identify|Look|Determine|Compare)\s', line, re.IGNORECASE):
                        plans.append(line)
        
        return plans if plans else ["Unable to parse plans, using original response"]

    def _verify_plan(self, plan: str, question: str, memory: str) -> Tuple[str, str, str, int]:
        """
        Plan Verifier: 验证单个plan
        
        Returns:
            (verdict, corrected_plan, evidence, num_retrievals)
            verdict: "supported" | "contradicted" | "insufficient"
        """
        retrievals_count = 0
        docs = []
        current_query = plan
        
        # 尝试检索相关文档
        for attempt in range(self.max_retrieval_attempts):
            # 检索
            retrieved_docs = self.retriever.batch_search([current_query], num=self.retrieval_topk)
            retrievals_count += 1
            
            if retrieved_docs and retrieved_docs[0]:
                docs = retrieved_docs[0]
                break
            else:
                # 检索失败,尝试改写查询
                if attempt < self.max_retrieval_attempts - 1:
                    current_query = self._rewrite_query(plan, attempt + 1)
        
        # 如果没有检索到文档
        if not docs:
            return "insufficient", plan, "No relevant documents found", retrievals_count
        
        # 基于检索到的文档进行验证
        verdict, corrected_plan, evidence = self._verify_with_docs(plan, docs, question, memory)
        
        return verdict, corrected_plan, evidence, retrievals_count

    def _rewrite_query(self, plan: str, attempt: int) -> str:
        """改写检索查询以提高召回"""
        system_prompt, user_prompt = self.prompt_loader.get_query_rewriter_prompt(plan, attempt)
        
        rewritten = self._call_generator(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=100
        )

        cleaned = self._remove_thinking_content(rewritten.strip())
        return cleaned if cleaned else plan

    def _verify_with_docs(self, plan: str, docs: List[Dict], question: str, memory: str) -> Tuple[str, str, str]:
        """
        基于检索到的文档验证plan
        
        Returns:
            (verdict, corrected_plan, evidence)
        """
        docs_text = "\n\n".join([
            f"Document {i+1}: {doc.get('contents', doc.get('text', ''))}"
            for i, doc in enumerate(docs[:5])
        ])
        
        system_prompt, user_prompt = self.prompt_loader.get_verifier_prompt(plan, docs_text)
        
        response = self._call_generator(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.verifier_temperature,
            max_tokens=300
        )

        # 移除思考内容
        response = self._remove_thinking_content(response)
        verdict, corrected_plan, evidence = self._parse_verification_response(response, plan)
        
        return verdict, corrected_plan, evidence

    def _parse_verification_response(self, response: str, original_plan: str) -> Tuple[str, str, str]:
        """解析验证响应"""
        verdict = "insufficient"
        corrected_plan = original_plan
        evidence = ""
        
        lines = response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.lower().startswith('verdict:'):
                verdict_text = line.split(':', 1)[1].strip().lower()
                if 'supported' in verdict_text:
                    verdict = "supported"
                elif 'contradicted' in verdict_text:
                    verdict = "contradicted"
                elif 'insufficient' in verdict_text:
                    verdict = "insufficient"
            elif line.lower().startswith('corrected statement:') or line.lower().startswith('corrected:'):
                corrected_plan = line.split(':', 1)[1].strip()
            elif line.lower().startswith('evidence:'):
                evidence = line.split(':', 1)[1].strip()
        
        return verdict, corrected_plan if corrected_plan else original_plan, evidence

    def _check_and_summarize_memory(self, memory: str) -> str:
        """检查记忆长度，如有必要进行摘要"""
        estimated_tokens = len(memory.split()) * 1.3
        
        if estimated_tokens > self.memory_max_tokens:
            system_prompt, user_prompt = self.prompt_loader.get_memory_summarizer_prompt(memory)
            
            summarized = self._call_generator(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=500
            )

            return self._remove_thinking_content(summarized.strip())
        
        return memory

    def _remove_thinking_content(self, text: str) -> str:
        """移除Qwen3思考模式产生的思考内容"""
        import re
        # 移除 <|think|>...<|think|> 格式的内容
        text = re.sub(r'<\|think\|>.*?<\|think\|>', '', text, flags=re.DOTALL)
        # 移除 <thinking>...</thinking> 格式的内容
        text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
        # 移除 "Okay, let's see..." 等思考前缀
        text = re.sub(r"^Okay,? let's see\.?\s*", '', text, flags=re.DOTALL)
        text = re.sub(r"^Let me think\.?\s*", '', text, flags=re.DOTALL)
        text = re.sub(r"^First,?\s+", '', text, flags=re.DOTALL)
        # 清理多余的空白和换行
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _generate_final_answer(self, question: str, memory: str) -> str:
        """基于记忆生成最终答案"""
        system_prompt, user_prompt = self.prompt_loader.get_final_answer_prompt(question, memory)
        
        answer = self._call_generator(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.final_answer_temperature,
            max_tokens=200
        )

        return self._remove_thinking_content(answer.strip())

    def _generate_best_effort_answer(self, question: str, memory: str) -> str:
        """在达到最大迭代次数时生成尽力回答"""
        system_prompt, user_prompt = self.prompt_loader.get_best_effort_answer_prompt(question, memory)
        
        answer = self._call_generator(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.final_answer_temperature,
            max_tokens=200
        )

        return self._remove_thinking_content(answer.strip())

    def _save_intermediate_data(self):
        """保存中间数据到文件"""
        import os
        os.makedirs(self.config['save_dir'], exist_ok=True)
        
        output_path = os.path.join(self.config['save_dir'], 'intermediate_data.jsonl')
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in self.intermediate_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"Intermediate data saved to: {output_path}")