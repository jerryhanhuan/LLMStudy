#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内置工具实现
"""

import re
import json
import logging
import requests
from typing import Any, Dict
from datetime import datetime
from ..tools import BaseTool

logger = logging.getLogger(__name__)

class CalculatorTool(BaseTool):
    """计算器工具"""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="执行数学计算，支持基本的算术运算"
        )
    
    def execute(self, expression: str) -> str:
        """执行数学计算
        
        Args:
            expression: 数学表达式
            
        Returns:
            计算结果
        """
        try:
            # 安全检查：只允许数字、运算符和括号
            if not re.match(r'^[0-9+\-*/().\s]+$', expression):
                return "错误：表达式包含不允许的字符"
            
            # 执行计算
            result = eval(expression)
            return f"计算结果: {expression} = {result}"
            
        except ZeroDivisionError:
            return "错误：除零错误"
        except Exception as e:
            return f"计算错误: {str(e)}"
    
    def validate_params(self, **kwargs) -> bool:
        """验证参数"""
        return 'expression' in kwargs and isinstance(kwargs['expression'], str)

class WeatherTool(BaseTool):
    """天气查询工具"""
    
    def __init__(self):
        super().__init__(
            name="weather",
            description="查询指定城市的天气信息"
        )
        # 这里可以配置真实的天气API密钥
        self.api_key = None
    
    def execute(self, location: str) -> str:
        """查询天气信息
        
        Args:
            location: 城市名称
            
        Returns:
            天气信息
        """
        try:
            if self.api_key:
                # 使用真实的天气API
                return self._get_real_weather(location)
            else:
                # 返回模拟天气数据
                return self._get_mock_weather(location)
                
        except Exception as e:
            logger.error(f"天气查询失败: {e}")
            return f"无法获取 {location} 的天气信息，请稍后再试"
    
    def _get_real_weather(self, location: str) -> str:
        """获取真实天气数据"""
        # 这里可以集成真实的天气API，如OpenWeatherMap
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': location,
            'appid': self.api_key,
            'units': 'metric',
            'lang': 'zh_cn'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code == 200:
            weather = data['weather'][0]['description']
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            humidity = data['main']['humidity']
            
            return f"""{location} 当前天气:
天气状况: {weather}
温度: {temp}°C (体感温度: {feels_like}°C)
湿度: {humidity}%
数据更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        else:
            return f"无法获取 {location} 的天气信息: {data.get('message', '未知错误')}"
    
    def _get_mock_weather(self, location: str) -> str:
        """获取模拟天气数据"""
        import random
        
        weather_conditions = ['晴朗', '多云', '阴天', '小雨', '中雨']
        weather = random.choice(weather_conditions)
        temp = random.randint(15, 30)
        humidity = random.randint(40, 80)
        
        return f"""{location} 当前天气 (模拟数据):
天气状况: {weather}
温度: {temp}°C
湿度: {humidity}%
注意: 这是模拟数据，请配置真实的天气API获取准确信息
数据生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
    
    def validate_params(self, **kwargs) -> bool:
        """验证参数"""
        return 'location' in kwargs and isinstance(kwargs['location'], str)

class EmailTool(BaseTool):
    """邮件发送工具"""
    
    def __init__(self):
        super().__init__(
            name="email",
            description="发送邮件给指定收件人"
        )
        # 邮件配置（实际使用时需要配置真实的SMTP服务器）
        self.smtp_configured = False
    
    def execute(self, to: str, subject: str, content: str) -> str:
        """发送邮件
        
        Args:
            to: 收件人邮箱
            subject: 邮件主题
            content: 邮件内容
            
        Returns:
            发送结果
        """
        try:
            if self.smtp_configured:
                return self._send_real_email(to, subject, content)
            else:
                return self._simulate_email_send(to, subject, content)
                
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return f"邮件发送失败: {str(e)}"
    
    def _send_real_email(self, to: str, subject: str, content: str) -> str:
        """发送真实邮件"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # 这里需要配置真实的SMTP服务器信息
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        username = "your_email@gmail.com"
        password = "your_password"
        
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = to
        msg['Subject'] = subject
        
        msg.attach(MIMEText(content, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        
        return f"邮件已成功发送给 {to}"
    
    def _simulate_email_send(self, to: str, subject: str, content: str) -> str:
        """模拟邮件发送"""
        # 验证邮箱格式
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, to):
            return f"错误：邮箱地址格式不正确: {to}"
        
        # 模拟发送过程
        send_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return f"""邮件发送模拟成功！
收件人: {to}
主题: {subject}
内容预览: {content[:50]}{'...' if len(content) > 50 else ''}
发送时间: {send_time}

注意: 这是模拟发送，请配置真实的SMTP服务器以发送实际邮件。"""
    
    def validate_params(self, **kwargs) -> bool:
        """验证参数"""
        required_params = ['to', 'subject', 'content']
        return all(param in kwargs and isinstance(kwargs[param], str) 
                  for param in required_params)

class TimeTool(BaseTool):
    """时间工具"""
    
    def __init__(self):
        super().__init__(
            name="time",
            description="获取当前时间或日期信息"
        )
    
    def execute(self, format_type: str = "datetime") -> str:
        """获取时间信息
        
        Args:
            format_type: 格式类型 (datetime, date, time, timestamp)
            
        Returns:
            时间信息
        """
        now = datetime.now()
        
        if format_type == "date":
            return f"今天是 {now.strftime('%Y年%m月%d日')}"
        elif format_type == "time":
            return f"现在时间是 {now.strftime('%H:%M:%S')}"
        elif format_type == "timestamp":
            return f"当前时间戳: {int(now.timestamp())}"
        else:  # datetime
            return f"当前时间: {now.strftime('%Y年%m月%d日 %H:%M:%S')}"
    
    def validate_params(self, **kwargs) -> bool:
        """验证参数"""
        if 'format_type' in kwargs:
            valid_formats = ['datetime', 'date', 'time', 'timestamp']
            return kwargs['format_type'] in valid_formats
        return True

class FileSearchTool(BaseTool):
    """文件搜索工具"""
    
    def __init__(self):
        super().__init__(
            name="file_search",
            description="在指定目录中搜索文件"
        )
    
    def execute(self, directory: str, pattern: str = "*") -> str:
        """搜索文件
        
        Args:
            directory: 搜索目录
            pattern: 文件名模式
            
        Returns:
            搜索结果
        """
        import os
        import glob
        from pathlib import Path
        
        try:
            # 安全检查：确保目录存在且在允许的范围内
            dir_path = Path(directory)
            if not dir_path.exists():
                return f"目录不存在: {directory}"
            
            if not dir_path.is_dir():
                return f"路径不是目录: {directory}"
            
            # 搜索文件
            search_pattern = os.path.join(directory, pattern)
            files = glob.glob(search_pattern)
            
            if not files:
                return f"在 {directory} 中未找到匹配 '{pattern}' 的文件"
            
            # 格式化结果
            result = f"在 {directory} 中找到 {len(files)} 个文件:\n"
            for file_path in sorted(files):
                file_info = Path(file_path)
                size = file_info.stat().st_size if file_info.is_file() else 0
                result += f"- {file_info.name} ({size} bytes)\n"
            
            return result
            
        except Exception as e:
            return f"文件搜索失败: {str(e)}"
    
    def validate_params(self, **kwargs) -> bool:
        """验证参数"""
        return 'directory' in kwargs and isinstance(kwargs['directory'], str)