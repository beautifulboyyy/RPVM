"""
RPVM Pipeline Implementation (Refactored)
Reflective Plan-Verify Memory for Multi-hop QA

重构后的架构：
- Planner: Judge判断 + Plan生成（两次LLM调用）
- Verifier: Rewrite + Retrieve + Verify
- Memory: 知识压缩 + 证据绑定（统一处理supported/contradicted）
- Generate: 基于已验证路径生成最终答案
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

    重构后的流程:
    1. Planner (2次LLM): Judge判断 -> Plan生成
    2. Verifier: Rewrite -> Retrieve -> Verify
    3. Memory: 知识压缩 + 证据绑定
    4. Generate: 生成最终答案
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

        # 初始化Prompt Loader（默认使用GPT35风格）
        prompt_dir = rpvm_config.get('prompt_dir', 'GPT35') if isinstance(rpvm_config, dict) else 'GPT35'
        self.prompt_loader = PromptLoader(prompts_dir=prompt_dir)
        self.prompt_style = self.prompt_loader.prompt_style

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
            # 本地 HF 模型：使用手动构建的 chat template
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

        重构后的流程:
        1. Planner: Judge判断 -> Plan生成（可能多个）
        2. Verifier: 对每个plan进行 Rewrite -> Retrieve -> Verify
        3. Memory: 知识压缩 + 证据绑定
        4. Generate: 生成最终答案

        Returns:
            包含最终答案、记忆、迭代历史等信息的字典
        """
        memory = ""
        iterations = []
        total_retrievals = 0

        for iter_idx in range(self.max_iter):
            # ==================== Step 1: Planner ====================
            # Step 1a: Judge判断 - 判断当前记忆是否足以回答问题
            judge_result = self._planner_judge(question, memory)

            if judge_result == "YES":
                # 记忆充足，生成最终答案
                final_answer = self._generate_final_answer(question, memory)
                iterations.append({
                    'iteration': iter_idx + 1,
                    'phase': 'Judge',
                    'judge_result': 'YES',
                    'final_answer': final_answer
                })
                break

            # Step 1b: Plan生成 - 仅在Judge=NO时生成所有需要的plans
            plans = self._planner_plan(question, memory)

            # 检查是否有有效的plans
            valid_plans = [p for p in plans if p and not p.startswith("Unable to parse")]
            if not valid_plans:
                # Plan解析失败，回到迭代开始
                iterations.append({
                    'iteration': iter_idx + 1,
                    'phase': 'Judge+Plan',
                    'judge_result': 'NO',
                    'plans': plans,
                    'memory_update': 'No update'
                })
                continue

            # 记录本轮迭代信息
            iter_info = {
                'iteration': iter_idx + 1,
                'phase': 'Judge+Plan',
                'judge_result': 'NO',
                'plans': valid_plans,
                'verifications': []
            }

            # ==================== Step 2: Verifier ====================
            # 对每个plan进行验证
            # 问题1修复：遇到第一个contradicted立即短路，停止后续plans验证
            short_circuit_due_to_contradiction = False

            for plan_idx, plan in enumerate(valid_plans):
                # Rewrite + Retrieve + Verify
                verdict, corrected_plan, evidence, retrievals = self._verify_plan(
                    plan, question, memory
                )
                total_retrievals += retrievals

                verification_info = {
                    'plan_index': plan_idx + 1,
                    'original_plan': plan,
                    'verdict': verdict,
                    'corrected_plan': corrected_plan,
                    'evidence': evidence,
                    'retrievals': retrievals
                }
                iter_info['verifications'].append(verification_info)

                # ==================== Step 3: Memory ====================
                # 仅在verdict=supported或contradicted时触发
                if verdict in ["supported", "contradicted"]:
                    # 获取文档文本用于Memory模块
                    docs_text = self._get_docs_text_for_memory(plan, question, memory)

                    # 调用Memory模块进行知识压缩+证据绑定
                    refined_memory = self._update_memory(
                        question=question,
                        plan=corrected_plan,
                        docs_text=docs_text,
                        memory=memory,
                        verdict=verdict
                    )

                    memory = refined_memory

                # 问题1修复：遇到contradicted立即短路，停止验证后续plans
                if verdict == "contradicted":
                    short_circuit_due_to_contradiction = True
                    break

            # 更新迭代信息
            if iter_info['verifications']:
                last_verdict = iter_info['verifications'][-1]['verdict']
                if last_verdict in ["supported", "contradicted"]:
                    iter_info['memory_update'] = 'Updated'
                else:
                    iter_info['memory_update'] = 'No update (all insufficient)'
            else:
                iter_info['memory_update'] = 'No update'

            iter_info['updated_memory'] = memory

            # contradicted情况：短路当前轮，回到Planner重新判断
            if short_circuit_due_to_contradiction:
                iter_info['short_circuit'] = True
                iterations.append(iter_info)
                continue

            iterations.append(iter_info)

        # ==================== Step 4: Generate ====================
        # 如果达到最大迭代次数或正常结束，生成最终答案
        if iter_idx == self.max_iter - 1 and judge_result != "YES":
            final_answer = self._generate_best_effort_answer(question, memory)

        return {
            'final_answer': final_answer,
            'final_memory': memory,
            'iterations': iterations,
            'total_retrievals': total_retrievals
        }

    # ==================== Planner Module ====================

    def _planner_judge(self, question: str, memory: str) -> str:
        """
        Planner Judge: 判断当前记忆是否足以回答问题

        Returns:
            "YES" 或 "NO"
        """
        system_prompt, user_prompt = self.prompt_loader.get_planner_judge_prompt(question, memory)

        response = self._call_generator(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,  # 低温保证确定性
            max_tokens=10     # 只需 YES/NO
        )

        response = response.strip().upper()
        if "YES" in response:
            return "YES"
        return "NO"

    def _planner_plan(self, question: str, memory: str) -> List[str]:
        """
        Planner Plan: 生成所有需要查询的子问题

        Returns:
            plan列表 或 包含解析失败标识的列表
        """
        system_prompt, user_prompt = self.prompt_loader.get_planner_plan_prompt(question, memory)

        response = self._call_generator(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.planner_temperature,
            max_tokens=512
        )

        # 解析plans（支持多个）
        plans = self._parse_plans(response)
        return plans if plans else ["Unable to parse plans"]

    def _parse_plans(self, response: str) -> List[str]:
        """从LLM响应中解析多个plan"""
        plans = []
        lines = response.strip().split('\n')

        for line in lines:
            line = line.strip()
            # 跳过空行
            if not line:
                continue

            # 匹配 "plan1: xxx" 格式
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

            # 匹配 "- " 开头的列表格式
            match = re.match(r'^-\s+(.+)$', line)
            if match:
                plan_text = match.group(1).strip()
                if plan_text:
                    plans.append(plan_text)

        return plans

    def _parse_single_plan(self, response: str) -> str:
        """从LLM响应中解析单个plan（已废弃，保留兼容）"""
        plans = self._parse_plans(response)
        return plans[0] if plans else ""

    # ==================== Verifier Module ====================

    def _verify_plan(self, plan: str, question: str, memory: str) -> Tuple[str, str, str, int]:
        """
        Plan Verifier: 验证单个plan

        流程:
        1. Rewrite: 从 Q 和 Plan 提取权威锚点 + 关系，生成检索词
        2. Retrieve: 基于优化后的检索词召回文档
        3. Verify: 将 Plan 与召回文档对比，输出判定结果

        Returns:
            (verdict, corrected_plan, evidence, num_retrievals)
            verdict: "supported" | "contradicted" | "insufficient"
        """
        # Step 1: Rewrite - 生成检索词（问题2修复：传入memory）
        query = self._extract_verification_query(question, plan, memory)

        # Step 2: Retrieve - 检索文档
        retrievals_count = 0
        retrieved_docs = self.retriever.batch_search([query], num=self.retrieval_topk)
        retrievals_count += 1

        docs = retrieved_docs[0] if retrieved_docs and retrieved_docs[0] else []

        # 如果没有检索到文档
        if not docs:
            return "insufficient", plan, "No relevant documents found", retrievals_count

        # Step 3: Verify - 验证plan
        verdict, corrected_plan, evidence = self._verify_with_docs(plan, docs, question, memory)

        return verdict, corrected_plan, evidence, retrievals_count

    def _extract_verification_query(self, question: str, plan: str, memory: str = "") -> str:
        """
        REAR Strategy: 从Memory和Question中提取权威实体，生成不含Plan幻觉的检索词

        Trust Protocol:
        - Trust Source: Q (Question) + M (Memory)
        - Verify Target: Plan (假设，可能有幻觉)
        - 从 Q/M 提取 Anchor Entity
        - 从 Plan 提取 Target Relation（丢弃宾语/数值）
        """
        # 从Memory中提取关键实体信息
        memory_context = memory if memory and memory.strip() else "None"

        system_prompt_template, user_prompt_template = self.prompt_loader.get_verifier_query_prompt(
            question=question,
            plan=plan,
            memory=memory_context
        )

        rewritten = self._call_generator(
            system_prompt=system_prompt_template,
            user_prompt=user_prompt_template,
            temperature=0.1,  # 低温保证确定性
            max_tokens=128    # 轻量任务
        )

        # 解析新格式输出
        lines = rewritten.strip().split('\n')
        query = None
        anchor_entity = None

        for line in lines:
            line = line.strip()
            if line.lower().startswith('anchor entity:'):
                anchor_entity = line.split(':', 1)[1].strip()
            elif line.lower().startswith('target relation:') or line.lower().startswith('relation:'):
                # 提取关系，丢弃宾语部分
                relation = line.split(':', 1)[1].strip()
                # 如果关系包含宾语（逗号或"of"后），只保留关系部分
                if ',' in relation:
                    relation = relation.split(',')[0].strip()
            elif line.lower().startswith('query:'):
                query = line.split(':', 1)[1].strip()

        # 如果成功解析到query，直接返回
        if query:
            return query

        # Fallback: 如果解析失败，使用Anchor Entity + 原始Question的简化
        if anchor_entity:
            # 从Question中提取关系类型
            if "who is" in question.lower():
                return f"Who is the {anchor_entity}"
            elif "when did" in question.lower():
                return f"When did {anchor_entity}"
            elif "where was" in question.lower():
                return f"Where was {anchor_entity}"
            else:
                return anchor_entity

        # 最终fallback
        return question

    def _verify_with_docs(self, plan: str, docs: List[Dict], question: str, memory: str) -> Tuple[str, str, str]:
        """
        基于检索到的文档验证plan
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
                # 去除首尾的单引号或双引号
                if (corrected_plan.startswith("'") and corrected_plan.endswith("'")) or \
                   (corrected_plan.startswith('"') and corrected_plan.endswith('"')):
                    corrected_plan = corrected_plan[1:-1].strip()
            elif line.lower().startswith('evidence:'):
                evidence = line.split(':', 1)[1].strip()

        return verdict, corrected_plan if corrected_plan else original_plan, evidence

    def _get_docs_text_for_memory(self, plan: str, question: str, memory: str) -> str:
        """
        重新检索获取文档文本用于Memory模块
        """
        query = self._extract_verification_query(question, plan, memory)
        retrieved_docs = self.retriever.batch_search([query], num=self.retrieval_topk)
        docs = retrieved_docs[0] if retrieved_docs and retrieved_docs[0] else []

        if not docs:
            return "No relevant documents found."

        docs_text = "\n\n".join([
            f"Document {i+1}: {doc.get('contents', doc.get('text', ''))}"
            for i, doc in enumerate(docs[:3])
        ])
        return docs_text

    # ==================== Memory Module ====================

    def _update_memory(self, question: str, plan: str, docs_text: str, memory: str, verdict: str) -> str:
        """
        Memory模块: 知识压缩 + 证据绑定

        仅在verdict=supported或contradicted时触发
        调用LLM进行知识压缩和证据绑定，输出精炼后的路径知识
        """
        system_prompt, user_prompt = self.prompt_loader.get_memory_prompt(
            question=question,
            plan=plan,
            docs_text=docs_text,
            memory=memory,
            verdict=verdict
        )

        refined_memory = self._call_generator(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=256
        )

        # 清理输出
        refined_memory = refined_memory.strip()
        refined_memory = re.sub(r'^\[Refined Path-Level Knowledge\]:\s*', '', refined_memory)

        # 追加到已有记忆
        if memory.strip():
            new_memory = f"{memory}\n{refined_memory}"
        else:
            new_memory = refined_memory

        # 检查记忆长度，如有必要进行摘要
        if self.enable_memory_summary:
            new_memory = self._check_and_summarize_memory(new_memory)

        return new_memory

    def _check_and_summarize_memory(self, memory: str) -> str:
        """检查记忆长度，如有必要进行摘要"""
        estimated_tokens = len(memory.split()) * 1.3

        if estimated_tokens > self.memory_max_tokens:
            # 使用简化的摘要策略：保留最近的路径知识
            lines = memory.split('\n')
            # 保留前3条最重要的路径知识
            key_lines = [l for l in lines if l.strip() and ('reasoning' in l.lower() or 'hop' in l.lower())]
            if len(key_lines) > 3:
                return '\n'.join(key_lines[-3:])  # 保留最近3条
            return memory

        return memory

    # ==================== Generate Module ====================

    def _generate_final_answer(self, question: str, memory: str) -> str:
        """
        Generate模块: 基于已验证路径生成最终答案
        """
        system_prompt, user_prompt = self.prompt_loader.get_generate_prompt(question, memory)

        answer = self._call_generator(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.final_answer_temperature,
            max_tokens=200
        )

        # 清理输出
        answer = answer.strip()
        answer = re.sub(r'^Answer:\s*', '', answer)

        return answer

    def _generate_best_effort_answer(self, question: str, memory: str) -> str:
        """
        在达到最大迭代次数时生成尽力回答
        """
        if self.prompt_style == 'GPT35':
            system_prompt, user_prompt = self.prompt_loader.get_generate_prompt(question, memory)
        else:
            system_prompt, user_prompt = self.prompt_loader.get_best_effort_answer_prompt(question, memory)

        answer = self._call_generator(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.final_answer_temperature,
            max_tokens=200
        )

        # 清理输出
        answer = answer.strip()
        answer = re.sub(r'^Answer:\s*', '', answer)

        return answer

    # ==================== Utility Methods ====================

    def _save_intermediate_data(self):
        """保存中间数据到文件"""
        import os
        os.makedirs(self.config['save_dir'], exist_ok=True)

        output_path = os.path.join(self.config['save_dir'], 'intermediate_data.jsonl')
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in self.intermediate_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        print(f"Intermediate data saved to: {output_path}")
