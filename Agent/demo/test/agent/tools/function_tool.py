#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
函数工具包装器
"""

import inspect
import logging
from typing import Any, Callable, Dict
from ..tools import BaseTool

logger = logging.getLogger(__name__)

class FunctionTool(BaseTool):
    """函数工具包装器
    
    将普通函数包装成工具，支持通过装饰器方式注册
    """
    
    def __init__(self, func: Callable):
        """初始化函数工具
        
        Args:
            func: 要包装的函数
        """
        self.func = func
        
        # 从函数获取名称和描述
        name = getattr(func, '__name__', 'unknown_function')
        description = getattr(func, '__doc__', f"执行函数 {name}") or f"执行函数 {name}"
        
        super().__init__(name, description.strip())
        
        # 分析函数签名
        self.signature = inspect.signature(func)
        self.parameters = self._analyze_parameters()
    
    def _analyze_parameters(self) -> Dict[str, Dict[str, Any]]:
        """分析函数参数
        
        Returns:
            参数信息字典
        """
        parameters = {}
        
        for param_name, param in self.signature.parameters.items():
            param_info = {
                "required": param.default == inspect.Parameter.empty,
                "type": "string"  # 默认类型
            }
            
            # 从类型注解推断类型
            if param.annotation != inspect.Parameter.empty:
                annotation = param.annotation
                
                if annotation == int:
                    param_info["type"] = "integer"
                elif annotation == float:
                    param_info["type"] = "number"
                elif annotation == bool:
                    param_info["type"] = "boolean"
                elif annotation == list:
                    param_info["type"] = "array"
                elif annotation == dict:
                    param_info["type"] = "object"
                elif hasattr(annotation, '__origin__'):
                    # 处理泛型类型，如 List[str], Dict[str, int] 等
                    origin = annotation.__origin__
                    if origin == list:
                        param_info["type"] = "array"
                    elif origin == dict:
                        param_info["type"] = "object"
            
            # 添加默认值信息
            if param.default != inspect.Parameter.empty:
                param_info["default"] = param.default
            
            parameters[param_name] = param_info
        
        return parameters
    
    def execute(self, **kwargs) -> Any:
        """执行函数
        
        Args:
            **kwargs: 函数参数
            
        Returns:
            函数执行结果
        """
        try:
            # 过滤参数，只传递函数需要的参数
            filtered_kwargs = {}
            for param_name in self.signature.parameters.keys():
                if param_name in kwargs:
                    filtered_kwargs[param_name] = kwargs[param_name]
            
            # 执行函数
            result = self.func(**filtered_kwargs)
            
            # 如果结果是None，返回成功消息
            if result is None:
                return f"函数 {self.name} 执行成功"
            
            return result
            
        except TypeError as e:
            if "missing" in str(e) and "required positional argument" in str(e):
                missing_param = str(e).split("'")[1]
                return f"错误：缺少必需参数 '{missing_param}'"
            else:
                return f"参数错误: {str(e)}"
        except Exception as e:
            logger.error(f"函数 {self.name} 执行失败: {e}")
            return f"函数执行失败: {str(e)}"
    
    def validate_params(self, **kwargs) -> bool:
        """验证参数
        
        Args:
            **kwargs: 参数
            
        Returns:
            是否有效
        """
        try:
            # 检查必需参数
            for param_name, param_info in self.parameters.items():
                if param_info["required"] and param_name not in kwargs:
                    logger.warning(f"缺少必需参数: {param_name}")
                    return False
            
            # 检查参数类型（基本检查）
            for param_name, value in kwargs.items():
                if param_name in self.parameters:
                    expected_type = self.parameters[param_name]["type"]
                    if not self._validate_type(value, expected_type):
                        logger.warning(f"参数 {param_name} 类型不匹配，期望 {expected_type}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"参数验证失败: {e}")
            return False
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """验证值的类型
        
        Args:
            value: 要验证的值
            expected_type: 期望的类型字符串
            
        Returns:
            是否匹配
        """
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "integer":
            return isinstance(value, int)
        elif expected_type == "number":
            return isinstance(value, (int, float))
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "object":
            return isinstance(value, dict)
        else:
            # 未知类型，默认通过
            return True
    
    def _get_parameters_schema(self) -> Dict[str, Any]:
        """获取参数模式
        
        Returns:
            参数模式字典
        """
        return self.parameters
    
    def get_function_info(self) -> Dict[str, Any]:
        """获取函数信息
        
        Returns:
            函数信息字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "module": getattr(self.func, '__module__', 'unknown'),
            "file": getattr(self.func, '__code__', {}).co_filename if hasattr(self.func, '__code__') else 'unknown',
            "line": getattr(self.func, '__code__', {}).co_firstlineno if hasattr(self.func, '__code__') else 0,
            "signature": str(self.signature),
            "parameters": self.parameters
        }

def tool_function(name: str = None, description: str = None):
    """工具函数装饰器
    
    Args:
        name: 工具名称（可选，默认使用函数名）
        description: 工具描述（可选，默认使用函数文档字符串）
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        # 设置工具元数据
        if name:
            func.__tool_name__ = name
        if description:
            func.__doc__ = description
        
        # 标记为工具函数
        func.__is_tool__ = True
        
        return func
    
    return decorator

def create_tool_from_function(func: Callable, name: str = None, description: str = None) -> FunctionTool:
    """从函数创建工具
    
    Args:
        func: 函数
        name: 工具名称（可选）
        description: 工具描述（可选）
    
    Returns:
        FunctionTool实例
    """
    # 创建函数副本以避免修改原函数
    import types
    func_copy = types.FunctionType(
        func.__code__,
        func.__globals__,
        name or func.__name__,
        func.__defaults__,
        func.__closure__
    )
    
    # 设置元数据
    if name:
        func_copy.__name__ = name
    if description:
        func_copy.__doc__ = description
    
    return FunctionTool(func_copy)