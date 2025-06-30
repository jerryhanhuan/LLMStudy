#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API数据模型
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ResponseStatus(str, Enum):
    """响应状态枚举"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"

# 基础模型
class BaseResponse(BaseModel):
    """基础响应模型"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = None

# 聊天相关模型
class Message(BaseModel):
    """消息模型"""
    role: MessageRole
    content: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    stream: bool = Field(False, description="是否流式响应")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="生成温度")
    max_tokens: Optional[int] = Field(None, gt=0, description="最大token数")
    tools_enabled: bool = Field(True, description="是否启用工具")
    memory_enabled: bool = Field(True, description="是否启用记忆")

class ChatResponse(BaseResponse):
    """聊天响应模型"""
    response: str = Field(..., description="AI回复")
    session_id: str = Field(..., description="会话ID")
    conversation_id: Optional[str] = Field(None, description="对话ID")
    tools_used: List[str] = Field(default_factory=list, description="使用的工具列表")
    execution_time: float = Field(..., description="执行时间（秒）")
    token_usage: Optional[Dict[str, int]] = Field(None, description="Token使用情况")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")

# 工具相关模型
class ToolParameter(BaseModel):
    """工具参数模型"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[str]] = None

class ToolInfo(BaseModel):
    """工具信息模型"""
    name: str
    description: str
    parameters: List[ToolParameter]
    category: Optional[str] = None
    version: Optional[str] = None
    enabled: bool = True

class ToolRequest(BaseModel):
    """工具执行请求模型"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    session_id: Optional[str] = Field(None, description="会话ID")
    timeout: Optional[int] = Field(None, gt=0, description="超时时间（秒）")

class ToolResponse(BaseResponse):
    """工具执行响应模型"""
    tool_name: str = Field(..., description="工具名称")
    result: Any = Field(..., description="执行结果")
    execution_time: float = Field(..., description="执行时间（秒）")
    success: bool = Field(..., description="是否成功")
    error_details: Optional[str] = Field(None, description="错误详情")

class ToolListResponse(BaseResponse):
    """工具列表响应模型"""
    tools: List[ToolInfo] = Field(..., description="工具列表")
    total_count: int = Field(..., description="工具总数")
    categories: List[str] = Field(default_factory=list, description="工具分类")

# 任务规划相关模型
class TaskInfo(BaseModel):
    """任务信息模型"""
    id: str
    name: str
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    dependencies: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3

class PlanInfo(BaseModel):
    """计划信息模型"""
    id: str
    name: str
    description: str
    tasks: List[TaskInfo]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class PlanRequest(BaseModel):
    """计划创建请求模型"""
    user_input: str = Field(..., description="用户输入")
    session_id: Optional[str] = Field(None, description="会话ID")
    auto_execute: bool = Field(False, description="是否自动执行")
    priority: Optional[str] = Field(None, description="优先级")

class PlanResponse(BaseResponse):
    """计划响应模型"""
    plan: PlanInfo = Field(..., description="计划信息")
    execution_result: Optional[Dict[str, Any]] = Field(None, description="执行结果")

class PlanListResponse(BaseResponse):
    """计划列表响应模型"""
    plans: List[PlanInfo] = Field(..., description="计划列表")
    total_count: int = Field(..., description="计划总数")
    status_counts: Dict[str, int] = Field(default_factory=dict, description="状态统计")

# 状态和统计相关模型
class AgentStatus(BaseModel):
    """Agent状态模型"""
    is_ready: bool
    uptime: float
    total_conversations: int
    total_tool_calls: int
    total_plans: int
    memory_usage: Dict[str, Any]
    active_sessions: int
    last_activity: Optional[datetime] = None

class SystemHealth(BaseModel):
    """系统健康状态模型"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_status: str
    database_status: str
    llm_status: str
    tools_status: Dict[str, str]

class StatusResponse(BaseResponse):
    """状态响应模型"""
    agent_status: AgentStatus = Field(..., description="Agent状态")
    system_health: Optional[SystemHealth] = Field(None, description="系统健康状态")

# 会话管理相关模型
class SessionInfo(BaseModel):
    """会话信息模型"""
    session_id: str
    created_at: datetime
    last_activity: datetime
    message_count: int
    tool_calls: int
    status: str
    metadata: Optional[Dict[str, Any]] = None

class SessionRequest(BaseModel):
    """会话请求模型"""
    session_id: Optional[str] = Field(None, description="会话ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="会话元数据")

class SessionResponse(BaseResponse):
    """会话响应模型"""
    session: SessionInfo = Field(..., description="会话信息")

class SessionListResponse(BaseResponse):
    """会话列表响应模型"""
    sessions: List[SessionInfo] = Field(..., description="会话列表")
    total_count: int = Field(..., description="会话总数")
    active_count: int = Field(..., description="活跃会话数")

# 记忆管理相关模型
class MemoryInfo(BaseModel):
    """记忆信息模型"""
    total_sessions: int
    total_messages: int
    total_contexts: int
    storage_type: str
    memory_size: Optional[float] = None  # MB

class MemoryRequest(BaseModel):
    """记忆请求模型"""
    session_id: Optional[str] = Field(None, description="会话ID")
    context_name: Optional[str] = Field(None, description="上下文名称")
    action: str = Field(..., description="操作类型: save, load, clear")

class MemoryResponse(BaseResponse):
    """记忆响应模型"""
    memory_info: MemoryInfo = Field(..., description="记忆信息")
    operation_result: Optional[Dict[str, Any]] = Field(None, description="操作结果")

# 配置相关模型
class ConfigInfo(BaseModel):
    """配置信息模型"""
    llm_model: str
    max_tokens: int
    temperature: float
    tools_enabled: bool
    memory_enabled: bool
    database_url: Optional[str] = None
    log_level: str
    api_version: str

class ConfigRequest(BaseModel):
    """配置请求模型"""
    config_key: str = Field(..., description="配置键")
    config_value: Any = Field(..., description="配置值")

class ConfigResponse(BaseResponse):
    """配置响应模型"""
    config: ConfigInfo = Field(..., description="配置信息")

# 错误模型
class ErrorDetail(BaseModel):
    """错误详情模型"""
    error_code: str
    error_type: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseResponse):
    """错误响应模型"""
    status: ResponseStatus = ResponseStatus.ERROR
    error: ErrorDetail = Field(..., description="错误详情")

# 流式响应模型
class StreamChunk(BaseModel):
    """流式响应块模型"""
    chunk_id: str
    content: str
    is_final: bool = False
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# 批量操作模型
class BatchRequest(BaseModel):
    """批量请求模型"""
    requests: List[Union[ChatRequest, ToolRequest, PlanRequest]]
    parallel: bool = Field(False, description="是否并行执行")
    fail_fast: bool = Field(True, description="是否快速失败")

class BatchResponse(BaseResponse):
    """批量响应模型"""
    results: List[Union[ChatResponse, ToolResponse, PlanResponse]]
    success_count: int
    failure_count: int
    execution_time: float

# 插件相关模型
class PluginInfo(BaseModel):
    """插件信息模型"""
    name: str
    version: str
    description: str
    author: str
    enabled: bool
    dependencies: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    config: Optional[Dict[str, Any]] = None

class PluginRequest(BaseModel):
    """插件请求模型"""
    plugin_name: str = Field(..., description="插件名称")
    action: str = Field(..., description="操作类型: enable, disable, reload, configure")
    config: Optional[Dict[str, Any]] = Field(None, description="插件配置")

class PluginResponse(BaseResponse):
    """插件响应模型"""
    plugin: PluginInfo = Field(..., description="插件信息")
    operation_result: Optional[Dict[str, Any]] = Field(None, description="操作结果")

class PluginListResponse(BaseResponse):
    """插件列表响应模型"""
    plugins: List[PluginInfo] = Field(..., description="插件列表")
    total_count: int = Field(..., description="插件总数")
    enabled_count: int = Field(..., description="启用的插件数")