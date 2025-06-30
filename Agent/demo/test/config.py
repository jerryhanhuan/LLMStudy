#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Config:
    """配置类"""
    
    # AI模型配置
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    MODEL_NAME: str = os.getenv('MODEL_NAME', 'gpt-3.5-turbo')
    MAX_TOKENS: int = int(os.getenv('MAX_TOKENS', '2000'))
    TEMPERATURE: float = float(os.getenv('TEMPERATURE', '0.7'))
    
    # 数据库配置
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///agent.db')
    
    # 服务配置
    SERVER_HOST: str = os.getenv('SERVER_HOST', 'localhost')
    SERVER_PORT: int = int(os.getenv('SERVER_PORT', '8000'))
    
    # 日志配置
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/agent.log')
    
    # Agent配置
    MAX_CONVERSATION_HISTORY: int = int(os.getenv('MAX_CONVERSATION_HISTORY', '50'))
    TOOL_TIMEOUT: int = int(os.getenv('TOOL_TIMEOUT', '30'))
    
    # 安全配置
    ENABLE_RATE_LIMIT: bool = os.getenv('ENABLE_RATE_LIMIT', 'true').lower() == 'true'
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '60'))
    
    def __post_init__(self):
        """初始化后的验证"""
        if not self.OPENAI_API_KEY:
            print("警告: 未设置 OPENAI_API_KEY 环境变量")
        
        # 确保日志目录存在
        log_dir = Path(self.LOG_FILE).parent
        log_dir.mkdir(exist_ok=True)
    
    @classmethod
    def from_file(cls, config_file: Optional[str] = None) -> 'Config':
        """从配置文件加载配置"""
        # 这里可以实现从YAML或JSON文件加载配置的逻辑
        # 目前使用环境变量
        return cls()
    
    def validate(self) -> bool:
        """验证配置的有效性"""
        required_fields = ['OPENAI_API_KEY']
        
        for field in required_fields:
            if not getattr(self, field):
                raise ValueError(f"必需的配置项 {field} 未设置")
        
        return True
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'model_name': self.MODEL_NAME,
            'max_tokens': self.MAX_TOKENS,
            'temperature': self.TEMPERATURE,
            'server_host': self.SERVER_HOST,
            'server_port': self.SERVER_PORT,
            'log_level': self.LOG_LEVEL
        }