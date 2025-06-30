#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具管理模块
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
import inspect
import json

logger = logging.getLogger(__name__)

class BaseTool(ABC):
    """工具基类"""
    
    def __init__(self, name: str, description: str):
        """初始化工具
        
        Args:
            name: 工具名称
            description: 工具描述
        """
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            执行结果
        """
        pass
    
    def validate_params(self, **kwargs) -> bool:
        """验证参数
        
        Args:
            **kwargs: 参数
            
        Returns:
            是否有效
        """
        return True
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具模式
        
        Returns:
            工具模式字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._get_parameters_schema()
        }
    
    def _get_parameters_schema(self) -> Dict[str, Any]:
        """获取参数模式"""
        # 通过检查execute方法的签名来生成参数模式
        sig = inspect.signature(self.execute)
        parameters = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'kwargs':
                continue
                
            param_info = {
                "type": "string",  # 默认类型
                "required": param.default == inspect.Parameter.empty
            }
            
            # 尝试从类型注解获取类型信息
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_info["type"] = "integer"
                elif param.annotation == float:
                    param_info["type"] = "number"
                elif param.annotation == bool:
                    param_info["type"] = "boolean"
                elif param.annotation == list:
                    param_info["type"] = "array"
                elif param.annotation == dict:
                    param_info["type"] = "object"
            
            parameters[param_name] = param_info
        
        return parameters

class ToolManager:
    """工具管理器"""
    
    def __init__(self):
        """初始化工具管理器"""
        self.tools: Dict[str, BaseTool] = {}
        self.tool_usage_stats: Dict[str, int] = {}
    
    def register_tool(self, tool: BaseTool):
        """注册工具
        
        Args:
            tool: 工具实例
        """
        if not isinstance(tool, BaseTool):
            raise ValueError("工具必须继承自BaseTool")
        
        self.tools[tool.name] = tool
        self.tool_usage_stats[tool.name] = 0
        logger.info(f"工具 '{tool.name}' 注册成功")
    
    def unregister_tool(self, tool_name: str):
        """注销工具
        
        Args:
            tool_name: 工具名称
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            del self.tool_usage_stats[tool_name]
            logger.info(f"工具 '{tool_name}' 注销成功")
        else:
            logger.warning(f"工具 '{tool_name}' 不存在")
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """执行工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            执行结果
        """
        if tool_name not in self.tools:
            raise ValueError(f"工具 '{tool_name}' 不存在")
        
        tool = self.tools[tool_name]
        
        try:
            # 验证参数
            if not tool.validate_params(**kwargs):
                raise ValueError(f"工具 '{tool_name}' 参数验证失败")
            
            # 执行工具
            logger.info(f"执行工具: {tool_name}, 参数: {kwargs}")
            result = tool.execute(**kwargs)
            
            # 更新使用统计
            self.tool_usage_stats[tool_name] += 1
            
            logger.info(f"工具 '{tool_name}' 执行成功")
            return result
            
        except Exception as e:
            logger.error(f"工具 '{tool_name}' 执行失败: {e}")
            raise
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具实例
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具实例或None
        """
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """列出所有工具名称
        
        Returns:
            工具名称列表
        """
        return list(self.tools.keys())
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具信息
        
        Returns:
            工具信息列表
        """
        return [tool.get_schema() for tool in self.tools.values()]
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具模式
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具模式或None
        """
        tool = self.get_tool(tool_name)
        return tool.get_schema() if tool else None
    
    def get_usage_stats(self) -> Dict[str, int]:
        """获取工具使用统计
        
        Returns:
            使用统计字典
        """
        return self.tool_usage_stats.copy()
    
    def search_tools(self, query: str) -> List[str]:
        """搜索工具
        
        Args:
            query: 搜索查询
            
        Returns:
            匹配的工具名称列表
        """
        query_lower = query.lower()
        matching_tools = []
        
        for tool_name, tool in self.tools.items():
            if (query_lower in tool_name.lower() or 
                query_lower in tool.description.lower()):
                matching_tools.append(tool_name)
        
        return matching_tools
    
    def validate_tool_call(self, tool_name: str, **kwargs) -> bool:
        """验证工具调用
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            是否有效
        """
        if tool_name not in self.tools:
            return False
        
        tool = self.tools[tool_name]
        return tool.validate_params(**kwargs)
    
    def get_tool_help(self, tool_name: str) -> Optional[str]:
        """获取工具帮助信息
        
        Args:
            tool_name: 工具名称
            
        Returns:
            帮助信息或None
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return None
        
        schema = tool.get_schema()
        help_text = f"工具名称: {schema['name']}\n"
        help_text += f"描述: {schema['description']}\n"
        help_text += "参数:\n"
        
        for param_name, param_info in schema['parameters'].items():
            required = "(必需)" if param_info.get('required', False) else "(可选)"
            help_text += f"  - {param_name} ({param_info['type']}) {required}\n"
        
        return help_text
    
    def export_tools_config(self) -> str:
        """导出工具配置
        
        Returns:
            JSON格式的工具配置
        """
        config = {
            "tools": [tool.get_schema() for tool in self.tools.values()],
            "usage_stats": self.tool_usage_stats
        }
        return json.dumps(config, indent=2, ensure_ascii=False)
    
    def clear_usage_stats(self):
        """清空使用统计"""
        self.tool_usage_stats = {name: 0 for name in self.tools.keys()}
        logger.info("工具使用统计已清空")