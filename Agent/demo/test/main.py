#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Agent Demo - 主应用程序入口

这是AI Agent演示程序的主入口文件，整合了所有核心功能模块。
"""

import asyncio
import sys
import signal
import argparse
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config_manager, init_config
from agent.core import AIAgent
from agent.llm_client import LLMClient
from agent.tools import ToolManager
from agent.memory import ConversationMemory
from agent.planner import TaskPlanner
from api.routes import create_app
from utils.logger import setup_logger

import uvicorn
from fastapi import FastAPI


class AgentApplication:
    """AI Agent应用程序主类"""
    
    def __init__(self, config_file: Optional[str] = None, env_file: Optional[str] = None):
        # 初始化配置
        self.config_manager = get_config_manager(config_file, env_file)
        self.config = self.config_manager.get_config()
        
        # 初始化日志
        self.logger = setup_logger(
            name="AgentApp",
            level=self.config.logging.level.value,
            log_file=self.config.logging.file_path if self.config.logging.file else None,
            console=self.config.logging.console
        )
        
        # 核心组件
        self.llm_client: Optional[LLMClient] = None
        self.tool_manager: Optional[ToolManager] = None
        self.memory: Optional[ConversationMemory] = None
        self.planner: Optional[TaskPlanner] = None
        self.agent: Optional[AIAgent] = None
        self.app: Optional[FastAPI] = None
        
        # 运行状态
        self.is_running = False
        self._shutdown_event = asyncio.Event()
        
        self.logger.info("AI Agent应用程序初始化完成")
    
    async def initialize(self):
        """初始化所有组件"""
        try:
            self.logger.info("开始初始化应用程序组件...")
            
            # 验证配置
            if not self.config_manager.validate_config():
                raise ValueError("配置验证失败")
            
            # 初始化LLM客户端
            self.logger.info("初始化LLM客户端...")
            self.llm_client = LLMClient(
                api_key=self.config.llm.api_key,
                api_base=self.config.llm.api_base,
                model=self.config.llm.model,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                timeout=self.config.llm.timeout
            )
            
            # 初始化工具管理器
            self.logger.info("初始化工具管理器...")
            self.tool_manager = ToolManager()
            
            # 注册内置工具
            if self.config.tools.calculator_enabled:
                from agent.tools.builtin import CalculatorTool
                self.tool_manager.register_tool(CalculatorTool())
            
            if self.config.tools.weather_enabled:
                from agent.tools.builtin import WeatherTool
                weather_tool = WeatherTool(
                    api_key=self.config.tools.weather_api_key,
                    api_url=self.config.tools.weather_api_url
                )
                self.tool_manager.register_tool(weather_tool)
            
            if self.config.tools.email_enabled:
                from agent.tools.builtin import EmailTool
                email_tool = EmailTool(
                    smtp_server=self.config.tools.email_smtp_server,
                    smtp_port=self.config.tools.email_smtp_port,
                    username=self.config.tools.email_username,
                    password=self.config.tools.email_password,
                    use_tls=self.config.tools.email_use_tls
                )
                self.tool_manager.register_tool(email_tool)
            
            if self.config.tools.time_enabled:
                from agent.tools.builtin import TimeTool
                self.tool_manager.register_tool(TimeTool())
            
            if self.config.tools.file_search_enabled:
                from agent.tools.builtin import FileSearchTool
                file_search_tool = FileSearchTool(
                    base_path=self.config.tools.file_search_base_path
                )
                self.tool_manager.register_tool(file_search_tool)
            
            # 初始化记忆系统
            self.logger.info("初始化记忆系统...")
            self.memory = ConversationMemory(
                storage_type=self.config.memory.storage_type.value,
                database_path=self.config.memory.database_path,
                max_history=self.config.memory.max_history
            )
            
            # 初始化任务规划器
            self.logger.info("初始化任务规划器...")
            self.planner = TaskPlanner(
                llm_client=self.llm_client,
                tool_manager=self.tool_manager
            )
            
            # 初始化AI Agent
            self.logger.info("初始化AI Agent...")
            self.agent = AIAgent(
                name=self.config.agent.name,
                description=self.config.agent.description,
                llm_client=self.llm_client,
                tool_manager=self.tool_manager if self.config.agent.enable_tools else None,
                memory=self.memory if self.config.agent.enable_memory else None,
                planner=self.planner if self.config.agent.enable_planning else None,
                max_history=self.config.agent.max_history,
                tool_timeout=self.config.agent.tool_timeout
            )
            
            # 初始化Web API
            self.logger.info("初始化Web API...")
            self.app = create_app(
                agent=self.agent,
                config=self.config
            )
            
            self.logger.info("所有组件初始化完成")
            
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            raise
    
    async def start_server(self):
        """启动Web服务器"""
        if not self.app:
            raise RuntimeError("应用程序未初始化")
        
        self.logger.info(f"启动Web服务器 {self.config.server.host}:{self.config.server.port}")
        
        config = uvicorn.Config(
            app=self.app,
            host=self.config.server.host,
            port=self.config.server.port,
            reload=self.config.server.reload and self.config.development.mode,
            workers=1,  # 在开发模式下使用单个worker
            log_level=self.config.logging.level.value.lower(),
            access_log=True
        )
        
        server = uvicorn.Server(config)
        
        # 设置信号处理
        def signal_handler(signum, frame):
            self.logger.info(f"收到信号 {signum}，开始关闭服务器...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        self.is_running = True
        
        try:
            # 启动服务器
            await server.serve()
        except Exception as e:
            self.logger.error(f"服务器运行错误: {e}")
            raise
        finally:
            self.is_running = False
            self.logger.info("Web服务器已停止")
    
    async def run_interactive(self):
        """运行交互式命令行模式"""
        if not self.agent:
            raise RuntimeError("Agent未初始化")
        
        self.logger.info("启动交互式命令行模式")
        print(f"\n欢迎使用 {self.config.agent.name}!")
        print(f"{self.config.agent.description}")
        print("输入 'quit' 或 'exit' 退出程序\n")
        
        session_id = "interactive_session"
        
        try:
            while True:
                try:
                    # 获取用户输入
                    user_input = input("用户: ").strip()
                    
                    if user_input.lower() in ['quit', 'exit', '退出']:
                        break
                    
                    if not user_input:
                        continue
                    
                    # 处理用户消息
                    response = await self.agent.process_message(
                        message=user_input,
                        session_id=session_id
                    )
                    
                    print(f"助手: {response.content}")
                    
                    # 如果有工具调用结果，显示详细信息
                    if response.tool_calls:
                        print("\n工具调用详情:")
                        for tool_call in response.tool_calls:
                            print(f"  - {tool_call.tool_name}: {tool_call.result}")
                    
                    print()  # 空行分隔
                    
                except KeyboardInterrupt:
                    print("\n\n收到中断信号，正在退出...")
                    break
                except Exception as e:
                    self.logger.error(f"处理消息时出错: {e}")
                    print(f"错误: {e}\n")
        
        except Exception as e:
            self.logger.error(f"交互式模式运行错误: {e}")
            raise
        finally:
            print("感谢使用，再见!")
    
    async def shutdown(self):
        """关闭应用程序"""
        self.logger.info("开始关闭应用程序...")
        
        try:
            # 关闭各个组件
            if self.memory:
                await self.memory.close()
            
            if self.llm_client:
                await self.llm_client.close()
            
            self.logger.info("应用程序关闭完成")
        
        except Exception as e:
            self.logger.error(f"关闭应用程序时出错: {e}")
    
    async def run(self, mode: str = "server"):
        """运行应用程序"""
        try:
            await self.initialize()
            
            if mode == "server":
                await self.start_server()
            elif mode == "interactive":
                await self.run_interactive()
            else:
                raise ValueError(f"不支持的运行模式: {mode}")
        
        except Exception as e:
            self.logger.error(f"应用程序运行失败: {e}")
            raise
        finally:
            await self.shutdown()


def create_argument_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="AI Agent Demo - 智能助手演示程序",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py                          # 启动Web服务器模式
  python main.py --mode interactive       # 启动交互式命令行模式
  python main.py --config config.json    # 使用指定配置文件
  python main.py --env .env.production    # 使用指定环境变量文件
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["server", "interactive"],
        default="server",
        help="运行模式 (默认: server)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径 (支持 .json, .toml, .yml/.yaml)"
    )
    
    parser.add_argument(
        "--env",
        type=str,
        default=".env",
        help="环境变量文件路径 (默认: .env)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        help="服务器主机地址 (覆盖配置文件)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        help="服务器端口 (覆盖配置文件)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="日志级别 (覆盖配置文件)"
    )
    
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="验证配置并退出"
    )
    
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="显示当前配置并退出"
    )
    
    return parser


async def main():
    """主函数"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    try:
        # 创建应用程序实例
        app = AgentApplication(
            config_file=args.config,
            env_file=args.env
        )
        
        # 应用命令行参数覆盖
        overrides = {}
        if args.host:
            overrides['server.host'] = args.host
        if args.port:
            overrides['server.port'] = args.port
        if args.debug:
            overrides['server.debug'] = True
            overrides['development.mode'] = True
        if args.log_level:
            from config import LogLevel
            overrides['logging.level'] = LogLevel(args.log_level)
        
        if overrides:
            app.config_manager.override_config(**overrides)
        
        # 处理特殊命令
        if args.validate_config:
            is_valid = app.config_manager.validate_config()
            print(f"配置验证结果: {'通过' if is_valid else '失败'}")
            if not is_valid:
                sys.exit(1)
            return
        
        if args.show_config:
            import json
            config_summary = app.config_manager.get_config_summary()
            print("当前配置:")
            print(json.dumps(config_summary, indent=2, ensure_ascii=False))
            return
        
        # 运行应用程序
        await app.run(mode=args.mode)
    
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容性）
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # 运行主程序
    asyncio.run(main())