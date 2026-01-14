"""
Prompt Loader Module
用于从文件加载RPVM pipeline使用的各类prompts
"""
import os
from typing import Dict

class PromptLoader:
    """从prompts目录加载所有prompt模板"""

    def __init__(self, prompts_dir: str = None):
        """
        初始化PromptLoader

        Args:
            prompts_dir: prompt文件目录路径。
                        如果指定了model_name参数，则使用 prompts/{model_name} 目录。
                        如果直接指定prompts_dir，则使用该目录。
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompts_base_dir = os.path.join(current_dir, 'prompts')

        if prompts_dir is None:
            # 默认使用openai的prompts
            self.prompts_dir = os.path.join(prompts_base_dir, 'openai')
        elif os.path.isabs(prompts_dir):
            # 绝对路径
            self.prompts_dir = prompts_dir
        else:
            # 相对路径，相对于prompts目录
            self.prompts_dir = os.path.join(prompts_base_dir, prompts_dir)

        self._prompts = {}
        self._load_all_prompts()
    
    def _load_all_prompts(self):
        """加载所有prompt文件"""
        prompt_files = {
            'planner_system': 'planner_system.md',
            'planner_few_shot_examples': 'planner_few_shot_examples.md',
            'planner_user_with_memory': 'planner_user_with_memory.md',
            'planner_user_without_memory': 'planner_user_without_memory.md',
            'verifier_system': 'verifier_system.md',
            'verifier_user': 'verifier_user.md',
            'verifier_query_system': 'verifier_query_system.md',
            'verifier_query_user': 'verifier_query_user.md',
            'memory_summarizer_system': 'memory_summarizer_system.md',
            'memory_summarizer_user': 'memory_summarizer_user.md',
            'final_answer_system': 'final_answer_system.md',
            'final_answer_user': 'final_answer_user.md',
            'best_effort_answer_system': 'best_effort_answer_system.md',
            'best_effort_answer_user_no_memory': 'best_effort_answer_user_no_memory.md',
            'best_effort_answer_user_with_memory': 'best_effort_answer_user_with_memory.md',
        }
        
        for key, filename in prompt_files.items():
            filepath = os.path.join(self.prompts_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self._prompts[key] = f.read()
            except FileNotFoundError:
                raise FileNotFoundError(f"Prompt file not found: {filepath}")
    
    def get(self, prompt_name: str, **kwargs) -> str:
        """
        获取prompt并进行格式化
        
        Args:
            prompt_name: prompt名称
            **kwargs: 用于格式化prompt的参数
        
        Returns:
            格式化后的prompt字符串
        """
        if prompt_name not in self._prompts:
            raise KeyError(f"Prompt '{prompt_name}' not found. Available prompts: {list(self._prompts.keys())}")
        
        prompt = self._prompts[prompt_name]
        
        if kwargs:
            return prompt.format(**kwargs)
        else:
            return prompt
    
    def get_planner_prompt(self, question: str, memory: str) -> tuple:
        """
        获取Planner的system和user prompt
        
        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.get('planner_system')
        few_shot_examples = self.get('planner_few_shot_examples')
        
        if memory.strip():
            user_prompt = self.get('planner_user_with_memory', 
                                  few_shot_examples=few_shot_examples,
                                  question=question,
                                  memory=memory)
        else:
            user_prompt = self.get('planner_user_without_memory',
                                  few_shot_examples=few_shot_examples,
                                  question=question)
        
        return system_prompt, user_prompt
    
    def get_verifier_prompt(self, plan: str, docs_text: str) -> tuple:
        """
        获取Verifier的system和user prompt

        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.get('verifier_system')
        user_prompt = self.get('verifier_user', plan=plan, docs_text=docs_text)
        return system_prompt, user_prompt

    def get_verifier_query_prompt(self, question: str, plan: str) -> tuple:
        """
        获取Verifier Query Extractor的system和user prompt
        用于从原始问题中提取权威实体，生成不包含plan幻觉的检索词

        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.get('verifier_query_system')
        user_prompt = self.get('verifier_query_user', question=question, plan=plan)
        return system_prompt, user_prompt

    def get_memory_summarizer_prompt(self, memory: str) -> tuple:
        """
        获取Memory Summarizer的system和user prompt
        
        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.get('memory_summarizer_system')
        user_prompt = self.get('memory_summarizer_user', memory=memory)
        return system_prompt, user_prompt
    
    def get_final_answer_prompt(self, question: str, memory: str) -> tuple:
        """
        获取Final Answer的system和user prompt
        
        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.get('final_answer_system')
        user_prompt = self.get('final_answer_user', question=question, memory=memory)
        return system_prompt, user_prompt
    
    def get_best_effort_answer_prompt(self, question: str, memory: str = None) -> tuple:
        """
        获取Best Effort Answer的system和user prompt
        
        Returns:
            (system_prompt, user_prompt)
        """
        system_prompt = self.get('best_effort_answer_system')
        
        if memory and memory.strip():
            user_prompt = self.get('best_effort_answer_user_with_memory',
                                  question=question,
                                  memory=memory)
        else:
            user_prompt = self.get('best_effort_answer_user_no_memory',
                                  question=question)
        
        return system_prompt, user_prompt
