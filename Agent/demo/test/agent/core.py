#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Agent 核心实现
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from .tools import ToolManager, BaseTool
from .memory import ConversationMemory
from .planner import TaskPlanner
from .llm_client import LLMClient

logger = logging.getLogger(__name__)

class AIAgent:
    """AI智能代理核心类"""
    
    def __init__(self, config):
        """初始化AI Agent
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.session_id = None
        
        # 初始化组件
        self.llm_client = LLMClient(config)
        self.tool_manager = ToolManager()
        self.memory = ConversationMemory(max_history=config.MAX_CONVERSATION_HISTORY)
        self.planner = TaskPlanner()
        
        # 注册默认工具
        self._register_default_tools()
        
        logger.info("AI Agent 初始化完成")
    
    def _register_default_tools(self):
        """注册默认工具"""
        from .tools.builtin import CalculatorTool, WeatherTool, EmailTool
        
        self.tool_manager.register_tool(CalculatorTool())
        self.tool_manager.register_tool(WeatherTool())
        self.tool_manager.register_tool(EmailTool())
    
    def chat(self, message: str, session_id: Optional[str] = None) -> str:
        """与AI Agent对话
        
        Args:
            message: 用户消息
            session_id: 会话ID
            
        Returns:
            AI Agent的回复
        """
        try:
            # 设置会话ID
            if session_id:
                self.session_id = session_id
            
            # 保存用户消息到记忆
            self.memory.add_message("user", message, session_id)
            
            # 分析用户意图和制定计划
            plan = self.planner.create_plan(message, self.tool_manager.get_available_tools())
            
            # 执行计划
            response = self._execute_plan(plan, message)
            
            # 保存AI回复到记忆
            self.memory.add_message("assistant", response, session_id)
            
            return response
            
        except Exception as e:
            logger.error(f"对话处理失败: {e}")
            return f"抱歉，处理您的请求时出现了错误: {str(e)}"
    
    def _execute_plan(self, plan: Dict[str, Any], original_message: str) -> str:
        """执行任务计划
        
        Args:
            plan: 任务计划
            original_message: 原始用户消息
            
        Returns:
            执行结果
        """
        try:
            if plan.get('type') == 'direct_response':
                # 直接回复，不需要工具
                return self._generate_direct_response(original_message)
            
            elif plan.get('type') == 'tool_usage':
                # 需要使用工具
                return self._execute_tool_plan(plan, original_message)
            
            elif plan.get('type') == 'multi_step':
                # 多步骤任务
                return self._execute_multi_step_plan(plan, original_message)
            
            else:
                return self._generate_direct_response(original_message)
                
        except Exception as e:
            logger.error(f"计划执行失败: {e}")
            return f"执行任务时出现错误: {str(e)}"
    
    def _generate_direct_response(self, message: str) -> str:
        """生成直接回复"""
        # 获取对话历史
        history = self.memory.get_conversation_history(self.session_id)
        
        # 构建提示词
        prompt = self._build_prompt(message, history)
        
        # 调用LLM生成回复
        response = self.llm_client.generate_response(prompt)
        
        return response
    
    def _execute_tool_plan(self, plan: Dict[str, Any], original_message: str) -> str:
        """执行工具使用计划"""
        tool_name = plan.get('tool_name')
        tool_params = plan.get('tool_params', {})
        
        # 执行工具
        tool_result = self.tool_manager.execute_tool(tool_name, **tool_params)
        
        # 基于工具结果生成最终回复
        return self._generate_response_with_tool_result(original_message, tool_result)
    
    def _execute_multi_step_plan(self, plan: Dict[str, Any], original_message: str) -> str:
        """执行多步骤计划"""
        steps = plan.get('steps', [])
        results = []
        
        for step in steps:
            if step.get('type') == 'tool':
                tool_result = self.tool_manager.execute_tool(
                    step.get('tool_name'),
                    **step.get('params', {})
                )
                results.append(f"步骤 {step.get('description', '')}: {tool_result}")
            
        # 汇总所有步骤结果
        return self._generate_summary_response(original_message, results)
    
    def _build_prompt(self, message: str, history: List[Dict]) -> str:
        """构建LLM提示词"""
        system_prompt = """
你是一个智能AI助手，能够理解用户需求并提供有帮助的回复。
你具有以下特点：
1. 友好、专业、有帮助
2. 能够理解上下文和对话历史
3. 提供准确、相关的信息
4. 承认不确定性，不编造信息
"""
        
        # 构建对话历史
        conversation = []
        for msg in history[-10:]:  # 只取最近10条消息
            conversation.append(f"{msg['role']}: {msg['content']}")
        
        history_text = "\n".join(conversation) if conversation else "(无对话历史)"
        
        prompt = f"""{system_prompt}

对话历史:
{history_text}

用户: {message}
助手:"""
        
        return prompt
    
    def _generate_response_with_tool_result(self, original_message: str, tool_result: Any) -> str:
        """基于工具结果生成回复"""
        prompt = f"""
用户请求: {original_message}
工具执行结果: {tool_result}

请基于工具执行结果，为用户生成一个友好、有帮助的回复。
"""
        
        return self.llm_client.generate_response(prompt)
    
    def _generate_summary_response(self, original_message: str, step_results: List[str]) -> str:
        """生成多步骤任务的汇总回复"""
        results_text = "\n".join(step_results)
        
        prompt = f"""
用户请求: {original_message}

执行步骤和结果:
{results_text}

请为用户生成一个汇总性的回复，说明任务的完成情况。
"""
        
        return self.llm_client.generate_response(prompt)
    
    def register_tool(self, tool: BaseTool):
        """注册新工具"""
        self.tool_manager.register_tool(tool)
        logger.info(f"工具 {tool.name} 注册成功")
    
    def tool(self, func: Callable) -> Callable:
        """工具装饰器"""
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # 创建工具对象并注册
        from .tools.function_tool import FunctionTool
        tool_obj = FunctionTool(func)
        self.register_tool(tool_obj)
        
        return wrapper
    
    def execute_task_chain(self, tasks: List[str]) -> str:
        """执行任务链"""
        results = []
        
        for i, task in enumerate(tasks, 1):
            logger.info(f"执行任务 {i}: {task}")
            result = self.chat(task)
            results.append(f"任务{i}结果: {result}")
        
        return "\n\n".join(results)
    
    def save_context(self, context_name: str):
        """保存对话上下文"""
        self.memory.save_context(context_name, self.session_id)
        logger.info(f"上下文 {context_name} 保存成功")
    
    def load_context(self, context_name: str):
        """加载对话上下文"""
        self.memory.load_context(context_name)
        logger.info(f"上下文 {context_name} 加载成功")
    
    def load_plugin(self, plugin_name: str):
        """加载插件"""
        # 这里可以实现插件加载逻辑
        logger.info(f"插件 {plugin_name} 加载成功")
    
    def list_tools(self) -> List[str]:
        """列出可用工具"""
        return self.tool_manager.list_tools()
    
    def get_status(self) -> Dict[str, Any]:
        """获取Agent状态"""
        return {
            'session_id': self.session_id,
            'available_tools': self.list_tools(),
            'conversation_count': len(self.memory.get_conversation_history(self.session_id)),
            'config': self.config.to_dict()
        }