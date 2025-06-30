#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM客户端模块
"""

import logging
import openai
from typing import Optional, Dict, Any, List
import time
import json

logger = logging.getLogger(__name__)

class LLMClient:
    """大语言模型客户端"""
    
    def __init__(self, config):
        """初始化LLM客户端
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.api_key = config.OPENAI_API_KEY
        self.model_name = config.MODEL_NAME
        self.max_tokens = config.MAX_TOKENS
        self.temperature = config.TEMPERATURE
        
        # 设置OpenAI API密钥
        if self.api_key:
            openai.api_key = self.api_key
        else:
            logger.warning("未设置OpenAI API密钥，将使用模拟响应")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """生成回复
        
        Args:
            prompt: 输入提示词
            **kwargs: 其他参数
            
        Returns:
            生成的回复文本
        """
        try:
            if not self.api_key:
                return self._mock_response(prompt)
            
            # 调用OpenAI API
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature),
                top_p=kwargs.get('top_p', 1.0),
                frequency_penalty=kwargs.get('frequency_penalty', 0.0),
                presence_penalty=kwargs.get('presence_penalty', 0.0)
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return self._fallback_response(prompt)
    
    def generate_chat_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """基于对话历史生成回复
        
        Args:
            messages: 对话消息列表
            **kwargs: 其他参数
            
        Returns:
            生成的回复文本
        """
        try:
            if not self.api_key:
                return self._mock_response(str(messages))
            
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                temperature=kwargs.get('temperature', self.temperature)
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"对话生成失败: {e}")
            return self._fallback_response(str(messages))
    
    def analyze_intent(self, message: str) -> Dict[str, Any]:
        """分析用户意图
        
        Args:
            message: 用户消息
            
        Returns:
            意图分析结果
        """
        prompt = f"""
请分析以下用户消息的意图，并以JSON格式返回结果：

用户消息: "{message}"

请返回包含以下字段的JSON：
- intent: 主要意图（如：question, request, command, chat等）
- entities: 提取的实体列表
- requires_tools: 是否需要使用工具（true/false）
- suggested_tools: 建议使用的工具列表
- confidence: 置信度（0-1）

只返回JSON，不要其他文字。
"""
        
        try:
            response = self.generate_response(prompt)
            # 尝试解析JSON
            return json.loads(response)
        except Exception as e:
            logger.error(f"意图分析失败: {e}")
            return {
                "intent": "unknown",
                "entities": [],
                "requires_tools": False,
                "suggested_tools": [],
                "confidence": 0.5
            }
    
    def generate_plan(self, message: str, available_tools: List[str]) -> Dict[str, Any]:
        """生成任务执行计划
        
        Args:
            message: 用户消息
            available_tools: 可用工具列表
            
        Returns:
            任务执行计划
        """
        tools_text = ", ".join(available_tools) if available_tools else "无"
        
        prompt = f"""
用户请求: "{message}"
可用工具: {tools_text}

请为此请求制定执行计划，以JSON格式返回：

{{
  "type": "计划类型（direct_response/tool_usage/multi_step）",
  "description": "计划描述",
  "tool_name": "需要使用的工具名称（如果适用）",
  "tool_params": {{"参数名": "参数值"}},
  "steps": [
    {{
      "type": "步骤类型",
      "description": "步骤描述",
      "tool_name": "工具名称",
      "params": {{}}
    }}
  ]
}}

只返回JSON，不要其他文字。
"""
        
        try:
            response = self.generate_response(prompt)
            return json.loads(response)
        except Exception as e:
            logger.error(f"计划生成失败: {e}")
            return {
                "type": "direct_response",
                "description": "直接回复"
            }
    
    def _mock_response(self, prompt: str) -> str:
        """模拟响应（当没有API密钥时使用）"""
        mock_responses = [
            "我理解您的请求，但目前我处于演示模式。请配置OpenAI API密钥以获得完整功能。",
            "这是一个模拟回复。在实际使用中，我会调用大语言模型来生成更智能的回复。",
            "感谢您的提问！这是演示模式的回复。配置API密钥后，我将能够提供更准确的帮助。",
            "我正在演示模式下运行。请设置OPENAI_API_KEY环境变量以启用完整的AI功能。"
        ]
        
        # 基于提示词长度选择回复
        index = len(prompt) % len(mock_responses)
        return mock_responses[index]
    
    def _fallback_response(self, prompt: str) -> str:
        """备用响应（当API调用失败时使用）"""
        return "抱歉，我暂时无法处理您的请求。请稍后再试，或检查网络连接和API配置。"
    
    def test_connection(self) -> bool:
        """测试LLM连接"""
        try:
            if not self.api_key:
                logger.info("未配置API密钥，使用模拟模式")
                return True
            
            # 发送测试请求
            response = self.generate_response("Hello, this is a test message.")
            return bool(response)
            
        except Exception as e:
            logger.error(f"LLM连接测试失败: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "api_configured": bool(self.api_key)
        }