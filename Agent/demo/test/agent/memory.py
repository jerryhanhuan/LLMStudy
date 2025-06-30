#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆管理模块
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import sqlite3
import threading

logger = logging.getLogger(__name__)

class ConversationMemory:
    """对话记忆管理器"""
    
    def __init__(self, max_history: int = 50, storage_type: str = "memory", db_path: str = "memory.db"):
        """初始化记忆管理器
        
        Args:
            max_history: 最大历史记录数
            storage_type: 存储类型 (memory, file, database)
            db_path: 数据库路径（当storage_type为database时使用）
        """
        self.max_history = max_history
        self.storage_type = storage_type
        self.db_path = db_path
        
        # 内存存储
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.contexts: Dict[str, Dict[str, Any]] = {}
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 初始化存储
        if storage_type == "database":
            self._init_database()
        elif storage_type == "file":
            self._ensure_storage_dir()
    
    def _init_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建对话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # 创建上下文表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contexts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_name TEXT UNIQUE NOT NULL,
                    session_id TEXT,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
            conn.close()
            
            logger.info(f"数据库初始化完成: {self.db_path}")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            # 降级到内存存储
            self.storage_type = "memory"
    
    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        storage_dir = Path("memory_storage")
        storage_dir.mkdir(exist_ok=True)
    
    def add_message(self, role: str, content: str, session_id: Optional[str] = None, metadata: Optional[Dict] = None):
        """添加消息到记忆
        
        Args:
            role: 角色 (user, assistant, system)
            content: 消息内容
            session_id: 会话ID
            metadata: 元数据
        """
        with self._lock:
            session_id = session_id or "default"
            timestamp = datetime.now().isoformat()
            
            message = {
                "role": role,
                "content": content,
                "timestamp": timestamp,
                "metadata": metadata or {}
            }
            
            if self.storage_type == "memory":
                self._add_message_memory(session_id, message)
            elif self.storage_type == "database":
                self._add_message_database(session_id, message)
            elif self.storage_type == "file":
                self._add_message_file(session_id, message)
    
    def _add_message_memory(self, session_id: str, message: Dict[str, Any]):
        """添加消息到内存"""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        self.conversations[session_id].append(message)
        
        # 限制历史记录长度
        if len(self.conversations[session_id]) > self.max_history:
            self.conversations[session_id] = self.conversations[session_id][-self.max_history:]
    
    def _add_message_database(self, session_id: str, message: Dict[str, Any]):
        """添加消息到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO conversations (session_id, role, content, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                message["role"],
                message["content"],
                message["timestamp"],
                json.dumps(message["metadata"])
            ))
            
            conn.commit()
            conn.close()
            
            # 清理旧记录
            self._cleanup_old_messages(session_id)
            
        except Exception as e:
            logger.error(f"数据库写入失败: {e}")
            # 降级到内存存储
            self._add_message_memory(session_id, message)
    
    def _add_message_file(self, session_id: str, message: Dict[str, Any]):
        """添加消息到文件"""
        try:
            file_path = Path("memory_storage") / f"{session_id}.json"
            
            # 读取现有数据
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    conversations = json.load(f)
            else:
                conversations = []
            
            # 添加新消息
            conversations.append(message)
            
            # 限制长度
            if len(conversations) > self.max_history:
                conversations = conversations[-self.max_history:]
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversations, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"文件写入失败: {e}")
            # 降级到内存存储
            self._add_message_memory(session_id, message)
    
    def get_conversation_history(self, session_id: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取对话历史
        
        Args:
            session_id: 会话ID
            limit: 限制返回数量
            
        Returns:
            对话历史列表
        """
        with self._lock:
            session_id = session_id or "default"
            
            if self.storage_type == "memory":
                history = self.conversations.get(session_id, [])
            elif self.storage_type == "database":
                history = self._get_history_database(session_id)
            elif self.storage_type == "file":
                history = self._get_history_file(session_id)
            else:
                history = []
            
            if limit:
                history = history[-limit:]
            
            return history
    
    def _get_history_database(self, session_id: str) -> List[Dict[str, Any]]:
        """从数据库获取历史"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT role, content, timestamp, metadata
                FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp
                LIMIT ?
            """, (session_id, self.max_history))
            
            rows = cursor.fetchall()
            conn.close()
            
            history = []
            for row in rows:
                history.append({
                    "role": row[0],
                    "content": row[1],
                    "timestamp": row[2],
                    "metadata": json.loads(row[3]) if row[3] else {}
                })
            
            return history
            
        except Exception as e:
            logger.error(f"数据库读取失败: {e}")
            return []
    
    def _get_history_file(self, session_id: str) -> List[Dict[str, Any]]:
        """从文件获取历史"""
        try:
            file_path = Path("memory_storage") / f"{session_id}.json"
            
            if not file_path.exists():
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"文件读取失败: {e}")
            return []
    
    def clear_conversation(self, session_id: Optional[str] = None):
        """清空对话历史
        
        Args:
            session_id: 会话ID，如果为None则清空所有
        """
        with self._lock:
            if session_id:
                session_id = session_id or "default"
                
                if self.storage_type == "memory":
                    self.conversations.pop(session_id, None)
                elif self.storage_type == "database":
                    self._clear_conversation_database(session_id)
                elif self.storage_type == "file":
                    self._clear_conversation_file(session_id)
            else:
                # 清空所有
                if self.storage_type == "memory":
                    self.conversations.clear()
                elif self.storage_type == "database":
                    self._clear_all_conversations_database()
                elif self.storage_type == "file":
                    self._clear_all_conversations_file()
    
    def _clear_conversation_database(self, session_id: str):
        """从数据库清空对话"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"数据库清空失败: {e}")
    
    def _clear_conversation_file(self, session_id: str):
        """从文件清空对话"""
        try:
            file_path = Path("memory_storage") / f"{session_id}.json"
            if file_path.exists():
                file_path.unlink()
                
        except Exception as e:
            logger.error(f"文件删除失败: {e}")
    
    def _clear_all_conversations_database(self):
        """清空数据库中所有对话"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM conversations")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"数据库清空失败: {e}")
    
    def _clear_all_conversations_file(self):
        """清空所有对话文件"""
        try:
            storage_dir = Path("memory_storage")
            for file_path in storage_dir.glob("*.json"):
                file_path.unlink()
                
        except Exception as e:
            logger.error(f"文件清空失败: {e}")
    
    def save_context(self, context_name: str, session_id: Optional[str] = None):
        """保存上下文
        
        Args:
            context_name: 上下文名称
            session_id: 会话ID
        """
        with self._lock:
            session_id = session_id or "default"
            history = self.get_conversation_history(session_id)
            
            context_data = {
                "session_id": session_id,
                "history": history,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            if self.storage_type == "database":
                self._save_context_database(context_name, context_data)
            else:
                self.contexts[context_name] = context_data
    
    def _save_context_database(self, context_name: str, context_data: Dict[str, Any]):
        """保存上下文到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO contexts (context_name, session_id, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                context_name,
                context_data["session_id"],
                json.dumps(context_data),
                context_data["created_at"],
                context_data["updated_at"]
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"上下文保存失败: {e}")
    
    def load_context(self, context_name: str) -> bool:
        """加载上下文
        
        Args:
            context_name: 上下文名称
            
        Returns:
            是否加载成功
        """
        with self._lock:
            try:
                if self.storage_type == "database":
                    context_data = self._load_context_database(context_name)
                else:
                    context_data = self.contexts.get(context_name)
                
                if not context_data:
                    logger.warning(f"上下文 '{context_name}' 不存在")
                    return False
                
                # 恢复对话历史
                session_id = context_data["session_id"]
                history = context_data["history"]
                
                if self.storage_type == "memory":
                    self.conversations[session_id] = history
                elif self.storage_type == "file":
                    self._restore_history_file(session_id, history)
                
                logger.info(f"上下文 '{context_name}' 加载成功")
                return True
                
            except Exception as e:
                logger.error(f"上下文加载失败: {e}")
                return False
    
    def _load_context_database(self, context_name: str) -> Optional[Dict[str, Any]]:
        """从数据库加载上下文"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT data FROM contexts WHERE context_name = ?", (context_name,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return json.loads(row[0])
            return None
            
        except Exception as e:
            logger.error(f"数据库上下文加载失败: {e}")
            return None
    
    def _restore_history_file(self, session_id: str, history: List[Dict[str, Any]]):
        """恢复历史到文件"""
        try:
            file_path = Path("memory_storage") / f"{session_id}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"历史恢复失败: {e}")
    
    def _cleanup_old_messages(self, session_id: str):
        """清理旧消息"""
        if self.storage_type == "database":
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 保留最新的max_history条记录
                cursor.execute("""
                    DELETE FROM conversations 
                    WHERE session_id = ? AND id NOT IN (
                        SELECT id FROM conversations 
                        WHERE session_id = ? 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    )
                """, (session_id, session_id, self.max_history))
                
                conn.commit()
                conn.close()
                
            except Exception as e:
                logger.error(f"清理旧消息失败: {e}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            "storage_type": self.storage_type,
            "max_history": self.max_history,
            "total_sessions": 0,
            "total_messages": 0,
            "total_contexts": 0
        }
        
        if self.storage_type == "memory":
            stats["total_sessions"] = len(self.conversations)
            stats["total_messages"] = sum(len(conv) for conv in self.conversations.values())
            stats["total_contexts"] = len(self.contexts)
        elif self.storage_type == "database":
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(DISTINCT session_id) FROM conversations")
                stats["total_sessions"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM conversations")
                stats["total_messages"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM contexts")
                stats["total_contexts"] = cursor.fetchone()[0]
                
                conn.close()
                
            except Exception as e:
                logger.error(f"统计信息获取失败: {e}")
        
        return stats