#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务规划模块
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import asyncio
import threading

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class Task:
    """任务数据类"""
    id: str
    name: str
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    dependencies: List[str] = None  # 依赖的任务ID列表
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None  # 超时时间（秒）
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """从字典创建任务"""
        data['priority'] = TaskPriority(data['priority'])
        data['status'] = TaskStatus(data['status'])
        return cls(**data)

@dataclass
class TaskPlan:
    """任务计划数据类"""
    id: str
    name: str
    description: str
    tasks: List[Task]
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'tasks': [task.to_dict() for task in self.tasks],
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskPlan':
        """从字典创建任务计划"""
        tasks = [Task.from_dict(task_data) for task_data in data['tasks']]
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            tasks=tasks,
            status=TaskStatus(data['status']),
            created_at=data['created_at'],
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at')
        )

class TaskPlanner:
    """任务规划器"""
    
    def __init__(self, tool_manager=None, llm_client=None):
        """初始化任务规划器
        
        Args:
            tool_manager: 工具管理器
            llm_client: LLM客户端
        """
        self.tool_manager = tool_manager
        self.llm_client = llm_client
        
        # 任务存储
        self.plans: Dict[str, TaskPlan] = {}
        self.running_tasks: Dict[str, Task] = {}
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 任务ID计数器
        self._task_counter = 0
        self._plan_counter = 0
    
    def _generate_task_id(self) -> str:
        """生成任务ID"""
        self._task_counter += 1
        return f"task_{self._task_counter:04d}"
    
    def _generate_plan_id(self) -> str:
        """生成计划ID"""
        self._plan_counter += 1
        return f"plan_{self._plan_counter:04d}"
    
    def analyze_user_intent(self, user_input: str) -> Dict[str, Any]:
        """分析用户意图
        
        Args:
            user_input: 用户输入
            
        Returns:
            意图分析结果
        """
        try:
            if self.llm_client:
                return self.llm_client.analyze_intent(user_input)
            else:
                # 简单的关键词匹配
                return self._simple_intent_analysis(user_input)
                
        except Exception as e:
            logger.error(f"意图分析失败: {e}")
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {},
                "requires_tools": False,
                "is_complex": False
            }
    
    def _simple_intent_analysis(self, user_input: str) -> Dict[str, Any]:
        """简单的意图分析"""
        user_input_lower = user_input.lower()
        
        # 工具相关关键词
        tool_keywords = {
            "calculator": ["计算", "算", "数学", "加", "减", "乘", "除"],
            "weather": ["天气", "温度", "下雨", "晴天", "阴天"],
            "email": ["邮件", "发送", "email", "mail"],
            "time": ["时间", "现在", "几点", "日期"],
            "file": ["文件", "搜索", "查找", "目录"]
        }
        
        # 复杂任务关键词
        complex_keywords = ["然后", "接着", "之后", "同时", "并且", "先", "再", "最后"]
        
        detected_tools = []
        for tool, keywords in tool_keywords.items():
            if any(keyword in user_input_lower for keyword in keywords):
                detected_tools.append(tool)
        
        is_complex = any(keyword in user_input_lower for keyword in complex_keywords)
        
        return {
            "intent": "task_execution" if detected_tools else "conversation",
            "confidence": 0.8 if detected_tools else 0.6,
            "entities": {"tools": detected_tools},
            "requires_tools": bool(detected_tools),
            "is_complex": is_complex or len(detected_tools) > 1
        }
    
    def create_task_plan(self, user_input: str, intent_analysis: Optional[Dict[str, Any]] = None) -> TaskPlan:
        """创建任务计划
        
        Args:
            user_input: 用户输入
            intent_analysis: 意图分析结果
            
        Returns:
            任务计划
        """
        with self._lock:
            if intent_analysis is None:
                intent_analysis = self.analyze_user_intent(user_input)
            
            plan_id = self._generate_plan_id()
            
            if intent_analysis.get("is_complex", False):
                # 复杂任务，需要分解
                tasks = self._decompose_complex_task(user_input, intent_analysis)
            else:
                # 简单任务
                tasks = self._create_simple_task(user_input, intent_analysis)
            
            plan = TaskPlan(
                id=plan_id,
                name=f"Plan for: {user_input[:50]}...",
                description=user_input,
                tasks=tasks
            )
            
            self.plans[plan_id] = plan
            logger.info(f"创建任务计划: {plan_id}, 包含 {len(tasks)} 个任务")
            
            return plan
    
    def _decompose_complex_task(self, user_input: str, intent_analysis: Dict[str, Any]) -> List[Task]:
        """分解复杂任务"""
        tasks = []
        
        if self.llm_client:
            try:
                # 使用LLM分解任务
                decomposition = self.llm_client.generate_task_plan(user_input)
                
                for i, step in enumerate(decomposition.get("steps", [])):
                    task = Task(
                        id=self._generate_task_id(),
                        name=step.get("name", f"Step {i+1}"),
                        description=step.get("description", ""),
                        tool_name=step.get("tool", "unknown"),
                        parameters=step.get("parameters", {}),
                        dependencies=step.get("dependencies", [])
                    )
                    tasks.append(task)
                    
            except Exception as e:
                logger.error(f"LLM任务分解失败: {e}")
                # 降级到简单分解
                tasks = self._simple_task_decomposition(user_input, intent_analysis)
        else:
            # 简单分解
            tasks = self._simple_task_decomposition(user_input, intent_analysis)
        
        return tasks
    
    def _simple_task_decomposition(self, user_input: str, intent_analysis: Dict[str, Any]) -> List[Task]:
        """简单任务分解"""
        tasks = []
        detected_tools = intent_analysis.get("entities", {}).get("tools", [])
        
        for i, tool in enumerate(detected_tools):
            task = Task(
                id=self._generate_task_id(),
                name=f"使用 {tool} 工具",
                description=f"执行 {tool} 相关操作",
                tool_name=tool,
                parameters=self._extract_tool_parameters(user_input, tool),
                dependencies=[tasks[i-1].id] if i > 0 else []
            )
            tasks.append(task)
        
        return tasks
    
    def _create_simple_task(self, user_input: str, intent_analysis: Dict[str, Any]) -> List[Task]:
        """创建简单任务"""
        detected_tools = intent_analysis.get("entities", {}).get("tools", [])
        
        if not detected_tools:
            # 没有检测到工具，创建对话任务
            return [Task(
                id=self._generate_task_id(),
                name="对话回复",
                description="生成对话回复",
                tool_name="conversation",
                parameters={"input": user_input}
            )]
        
        # 单个工具任务
        tool = detected_tools[0]
        return [Task(
            id=self._generate_task_id(),
            name=f"使用 {tool} 工具",
            description=f"执行 {tool} 操作",
            tool_name=tool,
            parameters=self._extract_tool_parameters(user_input, tool)
        )]
    
    def _extract_tool_parameters(self, user_input: str, tool_name: str) -> Dict[str, Any]:
        """提取工具参数"""
        # 简单的参数提取逻辑
        parameters = {"input": user_input}
        
        if tool_name == "calculator":
            # 提取数学表达式
            import re
            math_pattern = r'[0-9+\-*/().\s]+'
            matches = re.findall(math_pattern, user_input)
            if matches:
                parameters["expression"] = matches[0].strip()
        
        elif tool_name == "weather":
            # 提取城市名
            import re
            city_pattern = r'([\u4e00-\u9fa5]+市?|[A-Za-z\s]+)'
            matches = re.findall(city_pattern, user_input)
            if matches:
                parameters["city"] = matches[0]
        
        elif tool_name == "email":
            # 提取邮件相关信息
            import re
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, user_input)
            if emails:
                parameters["to"] = emails[0]
        
        return parameters
    
    async def execute_plan(self, plan_id: str) -> Dict[str, Any]:
        """执行任务计划
        
        Args:
            plan_id: 计划ID
            
        Returns:
            执行结果
        """
        with self._lock:
            plan = self.plans.get(plan_id)
            if not plan:
                raise ValueError(f"计划 {plan_id} 不存在")
            
            plan.status = TaskStatus.RUNNING
            plan.started_at = datetime.now().isoformat()
        
        try:
            logger.info(f"开始执行计划: {plan_id}")
            
            # 按依赖关系排序任务
            sorted_tasks = self._topological_sort(plan.tasks)
            
            results = {}
            
            for task in sorted_tasks:
                # 检查依赖是否完成
                if not self._check_dependencies(task, results):
                    task.status = TaskStatus.FAILED
                    task.error = "依赖任务未完成"
                    continue
                
                # 执行任务
                task_result = await self._execute_task(task)
                results[task.id] = task_result
            
            # 更新计划状态
            with self._lock:
                plan.completed_at = datetime.now().isoformat()
                
                # 检查所有任务是否成功
                if all(task.status == TaskStatus.COMPLETED for task in plan.tasks):
                    plan.status = TaskStatus.COMPLETED
                else:
                    plan.status = TaskStatus.FAILED
            
            logger.info(f"计划执行完成: {plan_id}, 状态: {plan.status.value}")
            
            return {
                "plan_id": plan_id,
                "status": plan.status.value,
                "results": results,
                "summary": self._generate_execution_summary(plan, results)
            }
            
        except Exception as e:
            logger.error(f"计划执行失败: {e}")
            
            with self._lock:
                plan.status = TaskStatus.FAILED
                plan.completed_at = datetime.now().isoformat()
            
            return {
                "plan_id": plan_id,
                "status": "failed",
                "error": str(e),
                "results": {}
            }
    
    def _topological_sort(self, tasks: List[Task]) -> List[Task]:
        """拓扑排序任务"""
        # 简单的拓扑排序实现
        task_map = {task.id: task for task in tasks}
        visited = set()
        result = []
        
        def dfs(task_id: str):
            if task_id in visited:
                return
            
            visited.add(task_id)
            task = task_map.get(task_id)
            
            if task:
                # 先访问依赖
                for dep_id in task.dependencies:
                    if dep_id in task_map:
                        dfs(dep_id)
                
                result.append(task)
        
        for task in tasks:
            dfs(task.id)
        
        return result
    
    def _check_dependencies(self, task: Task, results: Dict[str, Any]) -> bool:
        """检查任务依赖"""
        for dep_id in task.dependencies:
            if dep_id not in results:
                return False
            
            dep_result = results[dep_id]
            if not dep_result.get("success", False):
                return False
        
        return True
    
    async def _execute_task(self, task: Task) -> Dict[str, Any]:
        """执行单个任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        
        try:
            logger.info(f"执行任务: {task.id} - {task.name}")
            
            if task.tool_name == "conversation":
                # 对话任务
                result = await self._execute_conversation_task(task)
            elif self.tool_manager and self.tool_manager.has_tool(task.tool_name):
                # 工具任务
                result = await self._execute_tool_task(task)
            else:
                # 未知任务
                raise ValueError(f"未知的工具: {task.tool_name}")
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.result = result
            
            logger.info(f"任务完成: {task.id}")
            
            return {
                "task_id": task.id,
                "success": True,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"任务执行失败: {task.id} - {e}")
            
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now().isoformat()
            task.error = str(e)
            task.retry_count += 1
            
            return {
                "task_id": task.id,
                "success": False,
                "error": str(e)
            }
    
    async def _execute_conversation_task(self, task: Task) -> str:
        """执行对话任务"""
        if self.llm_client:
            return self.llm_client.generate_response(task.parameters.get("input", ""))
        else:
            return "我是一个AI助手，很高兴为您服务！"
    
    async def _execute_tool_task(self, task: Task) -> Any:
        """执行工具任务"""
        return self.tool_manager.execute_tool(task.tool_name, **task.parameters)
    
    def _generate_execution_summary(self, plan: TaskPlan, results: Dict[str, Any]) -> str:
        """生成执行摘要"""
        completed_tasks = sum(1 for task in plan.tasks if task.status == TaskStatus.COMPLETED)
        total_tasks = len(plan.tasks)
        
        summary = f"执行完成: {completed_tasks}/{total_tasks} 个任务成功"
        
        if plan.status == TaskStatus.COMPLETED:
            summary += "\n所有任务都已成功完成！"
        elif plan.status == TaskStatus.FAILED:
            failed_tasks = [task for task in plan.tasks if task.status == TaskStatus.FAILED]
            summary += f"\n{len(failed_tasks)} 个任务失败"
        
        return summary
    
    def get_plan_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """获取计划状态
        
        Args:
            plan_id: 计划ID
            
        Returns:
            计划状态信息
        """
        plan = self.plans.get(plan_id)
        if not plan:
            return None
        
        return {
            "plan_id": plan_id,
            "status": plan.status.value,
            "total_tasks": len(plan.tasks),
            "completed_tasks": sum(1 for task in plan.tasks if task.status == TaskStatus.COMPLETED),
            "failed_tasks": sum(1 for task in plan.tasks if task.status == TaskStatus.FAILED),
            "created_at": plan.created_at,
            "started_at": plan.started_at,
            "completed_at": plan.completed_at
        }
    
    def cancel_plan(self, plan_id: str) -> bool:
        """取消计划
        
        Args:
            plan_id: 计划ID
            
        Returns:
            是否取消成功
        """
        with self._lock:
            plan = self.plans.get(plan_id)
            if not plan:
                return False
            
            if plan.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return False
            
            plan.status = TaskStatus.CANCELLED
            plan.completed_at = datetime.now().isoformat()
            
            # 取消所有未完成的任务
            for task in plan.tasks:
                if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now().isoformat()
            
            logger.info(f"计划已取消: {plan_id}")
            return True
    
    def list_plans(self, status_filter: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
        """列出计划
        
        Args:
            status_filter: 状态过滤器
            
        Returns:
            计划列表
        """
        plans = []
        
        for plan in self.plans.values():
            if status_filter is None or plan.status == status_filter:
                plans.append({
                    "id": plan.id,
                    "name": plan.name,
                    "status": plan.status.value,
                    "total_tasks": len(plan.tasks),
                    "created_at": plan.created_at
                })
        
        return sorted(plans, key=lambda x: x["created_at"], reverse=True)
    
    def get_planner_stats(self) -> Dict[str, Any]:
        """获取规划器统计信息
        
        Returns:
            统计信息
        """
        total_plans = len(self.plans)
        status_counts = {}
        
        for status in TaskStatus:
            status_counts[status.value] = sum(
                1 for plan in self.plans.values() 
                if plan.status == status
            )
        
        total_tasks = sum(len(plan.tasks) for plan in self.plans.values())
        
        return {
            "total_plans": total_plans,
            "total_tasks": total_tasks,
            "status_distribution": status_counts,
            "running_tasks": len(self.running_tasks)
        }