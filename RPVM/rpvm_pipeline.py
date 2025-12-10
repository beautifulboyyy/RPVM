"""
RPVM Pipeline Implementation
Reflective Plan-Verify Memory for Multi-hop QA

基于FlashRAG框架实现RPVM方法
"""
import json
import re
from typing import List, Dict, Tuple, Optional
from tqdm import tqdm
from flashrag.pipeline import BasicPipeline
from flashrag.utils import get_retriever, get_generator
from flashrag.prompt import PromptTemplate


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
        
        # RPVM特定配置
        rpvm_config = config.get('rpvm_config', {})
        self.max_iter = rpvm_config.get('max_iter', 5)
        self.max_retrieval_attempts = rpvm_config.get('max_retrieval_attempts', 2)
        self.retrieval_topk = rpvm_config.get('retrieval_topk', 5)
        self.memory_max_tokens = rpvm_config.get('memory_max_tokens', 3000)
        self.enable_memory_summary = rpvm_config.get('enable_memory_summary', True)
        self.planner_temperature = rpvm_config.get('planner_temperature', 0.7)
        self.verifier_temperature = rpvm_config.get('verifier_temperature', 0.3)
        self.final_answer_temperature = rpvm_config.get('final_answer_temperature', 0.5)
        
        # 用于记录中间数据
        self.intermediate_data = []

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
        Reflective Planner: 基于问题和当前记忆生成推理计划链
        
        Returns:
            "ANSWER_READY" 或 计划列表 [plan1, plan2, ...]
        """
        planner_prompt = self._build_planner_prompt(question, memory)
        
        # 使用OpenAI生成器
        messages = [
            {"role": "system", "content": "You are a helpful assistant that plans reasoning chains for answering complex multi-hop questions."},
            {"role": "user", "content": planner_prompt}
        ]
        
        response = self.generator.generate(
            [messages],
            temperature=self.planner_temperature,
            max_tokens=512
        )[0]
        
        # 解析响应
        response = response.strip()
        if "ANSWER_READY" in response:
            return "ANSWER_READY"
        
        # 解析计划列表
        plans = self._parse_plans(response)
        return plans

    def _build_planner_prompt(self, question: str, memory: str) -> str:
        """构建Planner的prompt"""
        if memory.strip():
            prompt = f"""Given the question and the verified memory so far, determine the next reasoning steps needed.

Question: {question}

Verified Memory:
{memory}

Instructions:
1. If the memory contains enough information to answer the question, respond with exactly: ANSWER_READY
2. Otherwise, generate a logical reasoning chain as a numbered list of plans. Each plan should be a verifiable statement.
3. Format: List each plan on a new line starting with a number, e.g.:
   1. [First reasoning step]
   2. [Second reasoning step]

Your response:"""
        else:
            prompt = f"""Given the question, generate a logical reasoning chain to answer it.

Question: {question}

Instructions:
Generate a logical reasoning chain as a numbered list of plans. Each plan should be a verifiable statement that helps answer the question.

Format: List each plan on a new line starting with a number, e.g.:
1. [First reasoning step]
2. [Second reasoning step]

Your response:"""
        
        return prompt

    def _parse_plans(self, response: str) -> List[str]:
        """从LLM响应中解析计划列表"""
        plans = []
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            # 匹配 "1. xxx" 或 "1) xxx" 格式
            match = re.match(r'^(\d+)[\.\)]\s*(.+)$', line)
            if match:
                plan_text = match.group(2).strip()
                if plan_text:
                    plans.append(plan_text)
        
        # 如果没有解析到计划，尝试直接按行分割
        if not plans and response.strip():
            plans = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
        
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
            retrieved_docs = self.retriever.batch_search([current_query], topk=self.retrieval_topk)
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
        rewrite_prompt = f"""Rewrite the following statement into a more specific search query to find relevant documents.

Original statement: {plan}

Attempt {attempt}: Generate a different, more specific search query focusing on key entities and relationships.

Rewritten query:"""
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that rewrites queries for better document retrieval."},
            {"role": "user", "content": rewrite_prompt}
        ]
        
        rewritten = self.generator.generate(
            [messages],
            temperature=0.5,
            max_tokens=100
        )[0]
        
        return rewritten.strip() if rewritten.strip() else plan

    def _verify_with_docs(self, plan: str, docs: List[Dict], question: str, memory: str) -> Tuple[str, str, str]:
        """
        基于检索到的文档验证plan
        
        Returns:
            (verdict, corrected_plan, evidence)
        """
        # 构建验证prompt
        docs_text = "\n\n".join([
            f"Document {i+1}: {doc.get('contents', doc.get('text', ''))}"
            for i, doc in enumerate(docs[:5])  # 只使用前5个文档
        ])
        
        verify_prompt = f"""Based on the retrieved documents, verify the following statement.

Statement to verify: {plan}

Retrieved Documents:
{docs_text}

Instructions:
1. Determine if the statement is:
   - SUPPORTED: The documents provide evidence supporting this statement
   - CONTRADICTED: The documents contradict this statement
   - INSUFFICIENT: The documents don't provide enough information

2. If CONTRADICTED, provide the corrected version based on the documents.
3. If SUPPORTED or INSUFFICIENT, keep the original statement.

Respond in this exact format:
Verdict: [SUPPORTED/CONTRADICTED/INSUFFICIENT]
Corrected Statement: [the statement, corrected if needed]
Evidence: [brief explanation]

Your response:"""
        
        messages = [
            {"role": "system", "content": "You are a careful fact-checker that verifies statements against documents."},
            {"role": "user", "content": verify_prompt}
        ]
        
        response = self.generator.generate(
            [messages],
            temperature=self.verifier_temperature,
            max_tokens=300
        )[0]
        
        # 解析验证结果
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
            elif line.lower().startswith('corrected statement:'):
                corrected_plan = line.split(':', 1)[1].strip()
            elif line.lower().startswith('evidence:'):
                evidence = line.split(':', 1)[1].strip()
        
        return verdict, corrected_plan if corrected_plan else original_plan, evidence

    def _check_and_summarize_memory(self, memory: str) -> str:
        """检查记忆长度，如有必要进行摘要"""
        # 简单估计token数(英文约为单词数的1.3倍)
        estimated_tokens = len(memory.split()) * 1.3
        
        if estimated_tokens > self.memory_max_tokens:
            # 进行摘要
            summary_prompt = f"""Summarize the following verified facts into a concise memory, preserving all key information.

Memory to summarize:
{memory}

Provide a concise summary that retains all important facts:"""
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant that summarizes information concisely."},
                {"role": "user", "content": summary_prompt}
            ]
            
            summarized = self.generator.generate(
                [messages],
                temperature=0.3,
                max_tokens=500
            )[0]
            
            return summarized.strip()
        
        return memory

    def _generate_final_answer(self, question: str, memory: str) -> str:
        """基于记忆生成最终答案"""
        answer_prompt = f"""Based on the verified facts in memory, answer the question directly and concisely.

Question: {question}

Verified Memory:
{memory}

Provide a direct, concise answer to the question:"""
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that provides direct, accurate answers based on verified information."},
            {"role": "user", "content": answer_prompt}
        ]
        
        answer = self.generator.generate(
            [messages],
            temperature=self.final_answer_temperature,
            max_tokens=200
        )[0]
        
        return answer.strip()

    def _generate_best_effort_answer(self, question: str, memory: str) -> str:
        """在达到最大迭代次数时生成尽力回答"""
        if not memory.strip():
            # 如果没有记忆，直接用模型知识回答
            answer_prompt = f"""Answer the following question based on your knowledge. Be honest if you're uncertain.

Question: {question}

Answer:"""
        else:
            answer_prompt = f"""Based on the available verified facts (though incomplete), provide your best answer to the question. Acknowledge if information is incomplete.

Question: {question}

Verified Memory:
{memory}

Best effort answer:"""
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Provide the best answer you can, and be honest about uncertainty."},
            {"role": "user", "content": answer_prompt}
        ]
        
        answer = self.generator.generate(
            [messages],
            temperature=self.final_answer_temperature,
            max_tokens=200
        )[0]
        
        return answer.strip()

    def _save_intermediate_data(self):
        """保存中间数据到文件"""
        import os
        os.makedirs(self.config['save_dir'], exist_ok=True)
        
        output_path = os.path.join(self.config['save_dir'], 'intermediate_data.jsonl')
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in self.intermediate_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        print(f"Intermediate data saved to: {output_path}")
