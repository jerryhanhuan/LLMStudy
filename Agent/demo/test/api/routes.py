#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路由模块
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json

from .models import *
from .middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestValidationMiddleware
)
from ..agent import AIAgent
from ..config import Config

logger = logging.getLogger(__name__)

def create_app(config: Config, agent: AIAgent) -> FastAPI:
    """创建FastAPI应用
    
    Args:
        config: 配置对象
        agent: AI Agent实例
        
    Returns:
        FastAPI应用实例
    """
    app = FastAPI(
        title="AI Agent API",
        description="AI Agent RESTful API服务",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # 添加中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestValidationMiddleware, max_request_size=config.api.max_request_size)
    app.add_middleware(RateLimitMiddleware, 
                      requests_per_minute=config.api.rate_limit_per_minute,
                      requests_per_hour=config.api.rate_limit_per_hour)
    app.add_middleware(RequestLoggingMiddleware, 
                      log_requests=True, 
                      log_responses=config.logging.level == "DEBUG")
    
    # 存储配置和agent实例
    app.state.config = config
    app.state.agent = agent
    
    # 注册路由
    register_routes(app)
    
    return app

def register_routes(app: FastAPI):
    """注册所有路由"""
    
    # 健康检查
    @app.get("/health", response_model=StatusResponse, tags=["Health"])
    async def health_check():
        """健康检查接口"""
        agent: AIAgent = app.state.agent
        
        try:
            # 检查Agent状态
            agent_status = AgentStatus(
                is_ready=True,
                uptime=time.time() - getattr(agent, '_start_time', time.time()),
                total_conversations=len(agent.memory.conversations) if hasattr(agent, 'memory') else 0,
                total_tool_calls=getattr(agent, '_tool_call_count', 0),
                total_plans=len(agent.planner.plans) if hasattr(agent, 'planner') else 0,
                memory_usage=agent.memory.get_memory_stats() if hasattr(agent, 'memory') else {},
                active_sessions=len(agent.memory.conversations) if hasattr(agent, 'memory') else 0,
                last_activity=datetime.now()
            )
            
            return StatusResponse(
                status=ResponseStatus.SUCCESS,
                message="Service is healthy",
                agent_status=agent_status
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=500, detail="Service unhealthy")
    
    # 聊天接口
    @app.post("/chat", response_model=ChatResponse, tags=["Chat"])
    async def chat(request: ChatRequest, req: Request):
        """聊天接口"""
        start_time = time.time()
        agent: AIAgent = app.state.agent
        
        try:
            # 生成会话ID
            session_id = request.session_id or str(uuid.uuid4())
            
            # 调用Agent处理消息
            response = await agent.chat(
                message=request.message,
                session_id=session_id,
                context=request.context,
                tools_enabled=request.tools_enabled,
                memory_enabled=request.memory_enabled
            )
            
            execution_time = time.time() - start_time
            
            return ChatResponse(
                status=ResponseStatus.SUCCESS,
                message="Chat completed successfully",
                response=response.get("response", ""),
                session_id=session_id,
                tools_used=response.get("tools_used", []),
                execution_time=execution_time,
                request_id=getattr(req.state, 'request_id', None),
                metadata=response.get("metadata", {})
            )
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 流式聊天接口
    @app.post("/chat/stream", tags=["Chat"])
    async def chat_stream(request: ChatRequest, req: Request):
        """流式聊天接口"""
        agent: AIAgent = app.state.agent
        
        async def generate_stream():
            try:
                session_id = request.session_id or str(uuid.uuid4())
                
                # 这里应该实现流式响应逻辑
                # 目前简化为分块发送响应
                response = await agent.chat(
                    message=request.message,
                    session_id=session_id,
                    context=request.context,
                    tools_enabled=request.tools_enabled,
                    memory_enabled=request.memory_enabled
                )
                
                # 模拟流式输出
                content = response.get("response", "")
                chunk_size = 10
                
                for i in range(0, len(content), chunk_size):
                    chunk = StreamChunk(
                        chunk_id=str(uuid.uuid4()),
                        content=content[i:i+chunk_size],
                        is_final=(i + chunk_size >= len(content))
                    )
                    
                    yield f"data: {chunk.json()}\n\n"
                    await asyncio.sleep(0.1)  # 模拟延迟
                
            except Exception as e:
                error_chunk = StreamChunk(
                    chunk_id=str(uuid.uuid4()),
                    content=f"Error: {str(e)}",
                    is_final=True
                )
                yield f"data: {error_chunk.json()}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache"}
        )
    
    # 工具相关接口
    @app.get("/tools", response_model=ToolListResponse, tags=["Tools"])
    async def list_tools():
        """获取工具列表"""
        agent: AIAgent = app.state.agent
        
        try:
            tools_info = agent.list_tools()
            
            tools = []
            categories = set()
            
            for tool_name, tool_data in tools_info.items():
                tool_info = ToolInfo(
                    name=tool_name,
                    description=tool_data.get("description", ""),
                    parameters=[
                        ToolParameter(
                            name=param_name,
                            type=param_info.get("type", "string"),
                            description=param_info.get("description", ""),
                            required=param_info.get("required", True)
                        )
                        for param_name, param_info in tool_data.get("parameters", {}).items()
                    ],
                    category=tool_data.get("category", "general"),
                    enabled=True
                )
                tools.append(tool_info)
                categories.add(tool_info.category)
            
            return ToolListResponse(
                status=ResponseStatus.SUCCESS,
                message="Tools retrieved successfully",
                tools=tools,
                total_count=len(tools),
                categories=list(categories)
            )
            
        except Exception as e:
            logger.error(f"List tools error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/tools/execute", response_model=ToolResponse, tags=["Tools"])
    async def execute_tool(request: ToolRequest):
        """执行工具"""
        start_time = time.time()
        agent: AIAgent = app.state.agent
        
        try:
            # 执行工具
            result = agent.tool_manager.execute_tool(
                tool_name=request.tool_name,
                **request.parameters
            )
            
            execution_time = time.time() - start_time
            
            return ToolResponse(
                status=ResponseStatus.SUCCESS,
                message="Tool executed successfully",
                tool_name=request.tool_name,
                result=result,
                execution_time=execution_time,
                success=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool execution error: {e}")
            
            return ToolResponse(
                status=ResponseStatus.ERROR,
                message="Tool execution failed",
                tool_name=request.tool_name,
                result=None,
                execution_time=execution_time,
                success=False,
                error_details=str(e)
            )
    
    # 任务规划接口
    @app.post("/plans", response_model=PlanResponse, tags=["Planning"])
    async def create_plan(request: PlanRequest):
        """创建任务计划"""
        agent: AIAgent = app.state.agent
        
        try:
            # 创建计划
            plan = agent.planner.create_task_plan(
                user_input=request.user_input
            )
            
            # 转换为API模型
            plan_info = PlanInfo(
                id=plan.id,
                name=plan.name,
                description=plan.description,
                tasks=[
                    TaskInfo(
                        id=task.id,
                        name=task.name,
                        description=task.description,
                        tool_name=task.tool_name,
                        parameters=task.parameters,
                        dependencies=task.dependencies,
                        status=TaskStatus(task.status.value),
                        created_at=datetime.fromisoformat(task.created_at)
                    )
                    for task in plan.tasks
                ],
                status=TaskStatus(plan.status.value),
                created_at=datetime.fromisoformat(plan.created_at)
            )
            
            # 如果需要自动执行
            execution_result = None
            if request.auto_execute:
                execution_result = await agent.planner.execute_plan(plan.id)
            
            return PlanResponse(
                status=ResponseStatus.SUCCESS,
                message="Plan created successfully",
                plan=plan_info,
                execution_result=execution_result
            )
            
        except Exception as e:
            logger.error(f"Create plan error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/plans", response_model=PlanListResponse, tags=["Planning"])
    async def list_plans(status_filter: Optional[str] = None):
        """获取计划列表"""
        agent: AIAgent = app.state.agent
        
        try:
            # 获取计划列表
            status_enum = None
            if status_filter:
                try:
                    from ..agent.planner import TaskStatus as PlannerTaskStatus
                    status_enum = PlannerTaskStatus(status_filter)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
            
            plans_data = agent.planner.list_plans(status_filter=status_enum)
            
            plans = []
            status_counts = {}
            
            for plan_data in plans_data:
                plan = agent.planner.plans.get(plan_data["id"])
                if plan:
                    plan_info = PlanInfo(
                        id=plan.id,
                        name=plan.name,
                        description=plan.description,
                        tasks=[
                            TaskInfo(
                                id=task.id,
                                name=task.name,
                                description=task.description,
                                tool_name=task.tool_name,
                                parameters=task.parameters,
                                dependencies=task.dependencies,
                                status=TaskStatus(task.status.value),
                                created_at=datetime.fromisoformat(task.created_at)
                            )
                            for task in plan.tasks
                        ],
                        status=TaskStatus(plan.status.value),
                        created_at=datetime.fromisoformat(plan.created_at)
                    )
                    plans.append(plan_info)
                    
                    # 统计状态
                    status_key = plan.status.value
                    status_counts[status_key] = status_counts.get(status_key, 0) + 1
            
            return PlanListResponse(
                status=ResponseStatus.SUCCESS,
                message="Plans retrieved successfully",
                plans=plans,
                total_count=len(plans),
                status_counts=status_counts
            )
            
        except Exception as e:
            logger.error(f"List plans error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/plans/{plan_id}/execute", response_model=PlanResponse, tags=["Planning"])
    async def execute_plan(plan_id: str, background_tasks: BackgroundTasks):
        """执行计划"""
        agent: AIAgent = app.state.agent
        
        try:
            # 检查计划是否存在
            if plan_id not in agent.planner.plans:
                raise HTTPException(status_code=404, detail="Plan not found")
            
            # 异步执行计划
            async def execute_in_background():
                try:
                    await agent.planner.execute_plan(plan_id)
                except Exception as e:
                    logger.error(f"Background plan execution error: {e}")
            
            background_tasks.add_task(execute_in_background)
            
            # 获取计划信息
            plan = agent.planner.plans[plan_id]
            plan_info = PlanInfo(
                id=plan.id,
                name=plan.name,
                description=plan.description,
                tasks=[
                    TaskInfo(
                        id=task.id,
                        name=task.name,
                        description=task.description,
                        tool_name=task.tool_name,
                        parameters=task.parameters,
                        dependencies=task.dependencies,
                        status=TaskStatus(task.status.value),
                        created_at=datetime.fromisoformat(task.created_at)
                    )
                    for task in plan.tasks
                ],
                status=TaskStatus(plan.status.value),
                created_at=datetime.fromisoformat(plan.created_at)
            )
            
            return PlanResponse(
                status=ResponseStatus.SUCCESS,
                message="Plan execution started",
                plan=plan_info
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Execute plan error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/plans/{plan_id}", response_model=PlanResponse, tags=["Planning"])
    async def get_plan(plan_id: str):
        """获取计划详情"""
        agent: AIAgent = app.state.agent
        
        try:
            if plan_id not in agent.planner.plans:
                raise HTTPException(status_code=404, detail="Plan not found")
            
            plan = agent.planner.plans[plan_id]
            plan_info = PlanInfo(
                id=plan.id,
                name=plan.name,
                description=plan.description,
                tasks=[
                    TaskInfo(
                        id=task.id,
                        name=task.name,
                        description=task.description,
                        tool_name=task.tool_name,
                        parameters=task.parameters,
                        dependencies=task.dependencies,
                        status=TaskStatus(task.status.value),
                        created_at=datetime.fromisoformat(task.created_at),
                        started_at=datetime.fromisoformat(task.started_at) if task.started_at else None,
                        completed_at=datetime.fromisoformat(task.completed_at) if task.completed_at else None,
                        result=task.result,
                        error=task.error,
                        retry_count=task.retry_count,
                        max_retries=task.max_retries
                    )
                    for task in plan.tasks
                ],
                status=TaskStatus(plan.status.value),
                created_at=datetime.fromisoformat(plan.created_at),
                started_at=datetime.fromisoformat(plan.started_at) if plan.started_at else None,
                completed_at=datetime.fromisoformat(plan.completed_at) if plan.completed_at else None
            )
            
            return PlanResponse(
                status=ResponseStatus.SUCCESS,
                message="Plan retrieved successfully",
                plan=plan_info
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get plan error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/plans/{plan_id}", response_model=BaseResponse, tags=["Planning"])
    async def cancel_plan(plan_id: str):
        """取消计划"""
        agent: AIAgent = app.state.agent
        
        try:
            success = agent.planner.cancel_plan(plan_id)
            
            if not success:
                raise HTTPException(status_code=404, detail="Plan not found or cannot be cancelled")
            
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message="Plan cancelled successfully"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Cancel plan error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 会话管理接口
    @app.get("/sessions", response_model=SessionListResponse, tags=["Sessions"])
    async def list_sessions():
        """获取会话列表"""
        agent: AIAgent = app.state.agent
        
        try:
            sessions = []
            
            if hasattr(agent, 'memory'):
                for session_id, conversation in agent.memory.conversations.items():
                    session_info = SessionInfo(
                        session_id=session_id,
                        created_at=datetime.fromisoformat(conversation[0]["timestamp"]) if conversation else datetime.now(),
                        last_activity=datetime.fromisoformat(conversation[-1]["timestamp"]) if conversation else datetime.now(),
                        message_count=len(conversation),
                        tool_calls=sum(1 for msg in conversation if msg.get("metadata", {}).get("tool_used")),
                        status="active"
                    )
                    sessions.append(session_info)
            
            return SessionListResponse(
                status=ResponseStatus.SUCCESS,
                message="Sessions retrieved successfully",
                sessions=sessions,
                total_count=len(sessions),
                active_count=len(sessions)
            )
            
        except Exception as e:
            logger.error(f"List sessions error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/sessions/{session_id}", response_model=BaseResponse, tags=["Sessions"])
    async def clear_session(session_id: str):
        """清空会话"""
        agent: AIAgent = app.state.agent
        
        try:
            if hasattr(agent, 'memory'):
                agent.memory.clear_conversation(session_id)
            
            return BaseResponse(
                status=ResponseStatus.SUCCESS,
                message="Session cleared successfully"
            )
            
        except Exception as e:
            logger.error(f"Clear session error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 记忆管理接口
    @app.get("/memory/stats", response_model=MemoryResponse, tags=["Memory"])
    async def get_memory_stats():
        """获取记忆统计"""
        agent: AIAgent = app.state.agent
        
        try:
            if hasattr(agent, 'memory'):
                stats = agent.memory.get_memory_stats()
                memory_info = MemoryInfo(
                    total_sessions=stats.get("total_sessions", 0),
                    total_messages=stats.get("total_messages", 0),
                    total_contexts=stats.get("total_contexts", 0),
                    storage_type=stats.get("storage_type", "memory")
                )
            else:
                memory_info = MemoryInfo(
                    total_sessions=0,
                    total_messages=0,
                    total_contexts=0,
                    storage_type="none"
                )
            
            return MemoryResponse(
                status=ResponseStatus.SUCCESS,
                message="Memory stats retrieved successfully",
                memory_info=memory_info
            )
            
        except Exception as e:
            logger.error(f"Get memory stats error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 配置接口
    @app.get("/config", response_model=ConfigResponse, tags=["Config"])
    async def get_config():
        """获取配置信息"""
        config: Config = app.state.config
        
        try:
            config_info = ConfigInfo(
                llm_model=config.llm.model,
                max_tokens=config.llm.max_tokens,
                temperature=config.llm.temperature,
                tools_enabled=config.agent.enable_tools,
                memory_enabled=config.agent.enable_memory,
                log_level=config.logging.level,
                api_version="1.0.0"
            )
            
            return ConfigResponse(
                status=ResponseStatus.SUCCESS,
                message="Config retrieved successfully",
                config=config_info
            )
            
        except Exception as e:
            logger.error(f"Get config error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 统计接口
    @app.get("/stats", response_model=StatusResponse, tags=["Stats"])
    async def get_stats():
        """获取系统统计信息"""
        agent: AIAgent = app.state.agent
        
        try:
            # 获取Agent状态
            agent_status = AgentStatus(
                is_ready=True,
                uptime=time.time() - getattr(agent, '_start_time', time.time()),
                total_conversations=len(agent.memory.conversations) if hasattr(agent, 'memory') else 0,
                total_tool_calls=getattr(agent, '_tool_call_count', 0),
                total_plans=len(agent.planner.plans) if hasattr(agent, 'planner') else 0,
                memory_usage=agent.memory.get_memory_stats() if hasattr(agent, 'memory') else {},
                active_sessions=len(agent.memory.conversations) if hasattr(agent, 'memory') else 0,
                last_activity=datetime.now()
            )
            
            return StatusResponse(
                status=ResponseStatus.SUCCESS,
                message="Stats retrieved successfully",
                agent_status=agent_status
            )
            
        except Exception as e:
            logger.error(f"Get stats error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 批量操作接口
    @app.post("/batch", response_model=BatchResponse, tags=["Batch"])
    async def batch_operation(request: BatchRequest):
        """批量操作接口"""
        start_time = time.time()
        
        try:
            results = []
            success_count = 0
            failure_count = 0
            
            if request.parallel:
                # 并行执行
                tasks = []
                for req in request.requests:
                    if isinstance(req, ChatRequest):
                        tasks.append(chat(req, Request({"type": "http"})))
                    elif isinstance(req, ToolRequest):
                        tasks.append(execute_tool(req))
                    elif isinstance(req, PlanRequest):
                        tasks.append(create_plan(req))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        failure_count += 1
                    else:
                        success_count += 1
            else:
                # 串行执行
                for req in request.requests:
                    try:
                        if isinstance(req, ChatRequest):
                            result = await chat(req, Request({"type": "http"}))
                        elif isinstance(req, ToolRequest):
                            result = await execute_tool(req)
                        elif isinstance(req, PlanRequest):
                            result = await create_plan(req)
                        else:
                            raise ValueError(f"Unsupported request type: {type(req)}")
                        
                        results.append(result)
                        success_count += 1
                        
                    except Exception as e:
                        if request.fail_fast:
                            raise
                        
                        results.append(str(e))
                        failure_count += 1
            
            execution_time = time.time() - start_time
            
            return BatchResponse(
                status=ResponseStatus.SUCCESS,
                message="Batch operation completed",
                results=results,
                success_count=success_count,
                failure_count=failure_count,
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Batch operation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return app