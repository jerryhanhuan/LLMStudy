#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API中间件模块
"""

import time
import uuid
import logging
import traceback
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
import jwt
from datetime import datetime, timedelta
import hashlib
import hmac

from .models import ErrorResponse, ErrorDetail, ResponseStatus

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    def __init__(self, app, log_requests: bool = True, log_responses: bool = False):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 记录请求信息
        if self.log_requests:
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            
            logger.info(
                f"Request started - ID: {request_id}, "
                f"Method: {request.method}, "
                f"URL: {request.url}, "
                f"Client IP: {client_ip}, "
                f"User-Agent: {user_agent}"
            )
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            # 记录响应信息
            if self.log_responses:
                logger.info(
                    f"Request completed - ID: {request_id}, "
                    f"Status: {response.status_code}, "
                    f"Process Time: {process_time:.3f}s"
                )
            
            return response
            
        except Exception as e:
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录错误
            logger.error(
                f"Request failed - ID: {request_id}, "
                f"Error: {str(e)}, "
                f"Process Time: {process_time:.3f}s, "
                f"Traceback: {traceback.format_exc()}"
            )
            
            # 返回错误响应
            error_response = ErrorResponse(
                status=ResponseStatus.ERROR,
                message="Internal server error",
                request_id=request_id,
                error=ErrorDetail(
                    error_code="INTERNAL_ERROR",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=traceback.format_exc()
                )
            )
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=error_response.dict(),
                headers={
                    "X-Request-ID": request_id,
                    "X-Process-Time": str(process_time)
                }
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 返回直接连接的IP
        return request.client.host if request.client else "unknown"

class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # 存储请求记录
        self.request_records: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # 检查速率限制
        if self._is_rate_limited(client_ip, current_time):
            error_response = ErrorResponse(
                status=ResponseStatus.ERROR,
                message="Rate limit exceeded",
                error=ErrorDetail(
                    error_code="RATE_LIMIT_EXCEEDED",
                    error_type="RateLimitError",
                    error_message="Too many requests. Please try again later."
                )
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=error_response.dict(),
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit-Minute": str(self.requests_per_minute),
                    "X-RateLimit-Limit-Hour": str(self.requests_per_hour)
                }
            )
        
        # 记录请求
        self._record_request(client_ip, current_time)
        
        # 处理请求
        response = await call_next(request)
        
        # 添加速率限制头
        minute_count = self._get_request_count(client_ip, current_time, 60)
        hour_count = self._get_request_count(client_ip, current_time, 3600)
        
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, self.requests_per_minute - minute_count))
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(max(0, self.requests_per_hour - hour_count))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """检查是否超过速率限制"""
        minute_count = self._get_request_count(client_ip, current_time, 60)
        hour_count = self._get_request_count(client_ip, current_time, 3600)
        
        return minute_count >= self.requests_per_minute or hour_count >= self.requests_per_hour
    
    def _get_request_count(self, client_ip: str, current_time: float, window_seconds: int) -> int:
        """获取时间窗口内的请求数量"""
        if client_ip not in self.request_records:
            return 0
        
        # 清理过期记录
        cutoff_time = current_time - window_seconds
        self.request_records[client_ip] = [
            timestamp for timestamp in self.request_records[client_ip]
            if timestamp > cutoff_time
        ]
        
        return len(self.request_records[client_ip])
    
    def _record_request(self, client_ip: str, current_time: float):
        """记录请求"""
        if client_ip not in self.request_records:
            self.request_records[client_ip] = []
        
        self.request_records[client_ip].append(current_time)
        
        # 限制记录数量，避免内存泄漏
        if len(self.request_records[client_ip]) > self.requests_per_hour * 2:
            self.request_records[client_ip] = self.request_records[client_ip][-self.requests_per_hour:]

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """认证中间件"""
    
    def __init__(self, app, secret_key: str, algorithm: str = "HS256", 
                 excluded_paths: Optional[list] = None):
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.excluded_paths = excluded_paths or ["/docs", "/redoc", "/openapi.json", "/health"]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 检查是否需要认证
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # 获取认证头
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return self._unauthorized_response("Missing authorization header")
        
        # 解析token
        try:
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                return self._unauthorized_response("Invalid authentication scheme")
            
            # 验证token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查token是否过期
            if "exp" in payload and payload["exp"] < time.time():
                return self._unauthorized_response("Token expired")
            
            # 将用户信息添加到请求状态
            request.state.user = payload
            
        except ValueError:
            return self._unauthorized_response("Invalid authorization header format")
        except jwt.InvalidTokenError as e:
            return self._unauthorized_response(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return self._unauthorized_response("Authentication failed")
        
        return await call_next(request)
    
    def _is_excluded_path(self, path: str) -> bool:
        """检查路径是否排除在认证之外"""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    def _unauthorized_response(self, message: str) -> JSONResponse:
        """返回未授权响应"""
        error_response = ErrorResponse(
            status=ResponseStatus.ERROR,
            message="Unauthorized",
            error=ErrorDetail(
                error_code="UNAUTHORIZED",
                error_type="AuthenticationError",
                error_message=message
            )
        )
        
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=error_response.dict(),
            headers={"WWW-Authenticate": "Bearer"}
        )

class CORSMiddleware(BaseHTTPMiddleware):
    """CORS中间件"""
    
    def __init__(self, app, allow_origins: list = None, allow_methods: list = None, 
                 allow_headers: list = None, allow_credentials: bool = True):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        origin = request.headers.get("origin")
        
        # 处理预检请求
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(response, origin)
            return response
        
        # 处理实际请求
        response = await call_next(request)
        self._add_cors_headers(response, origin)
        
        return response
    
    def _add_cors_headers(self, response: Response, origin: Optional[str]):
        """添加CORS头"""
        # 检查origin是否允许
        if origin and ("*" in self.allow_origins or origin in self.allow_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response

class APIKeyMiddleware(BaseHTTPMiddleware):
    """API密钥中间件"""
    
    def __init__(self, app, api_keys: Dict[str, Dict[str, Any]], 
                 excluded_paths: Optional[list] = None):
        super().__init__(app)
        self.api_keys = api_keys  # {api_key: {"name": "client_name", "permissions": [...]}}
        self.excluded_paths = excluded_paths or ["/docs", "/redoc", "/openapi.json", "/health"]
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 检查是否需要API密钥
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # 获取API密钥
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        
        if not api_key:
            return self._unauthorized_response("Missing API key")
        
        # 验证API密钥
        if api_key not in self.api_keys:
            return self._unauthorized_response("Invalid API key")
        
        # 将API密钥信息添加到请求状态
        request.state.api_key_info = self.api_keys[api_key]
        
        return await call_next(request)
    
    def _is_excluded_path(self, path: str) -> bool:
        """检查路径是否排除在API密钥验证之外"""
        return any(path.startswith(excluded) for excluded in self.excluded_paths)
    
    def _unauthorized_response(self, message: str) -> JSONResponse:
        """返回未授权响应"""
        error_response = ErrorResponse(
            status=ResponseStatus.ERROR,
            message="Unauthorized",
            error=ErrorDetail(
                error_code="INVALID_API_KEY",
                error_type="AuthenticationError",
                error_message=message
            )
        )
        
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=error_response.dict()
        )

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """请求验证中间件"""
    
    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_request_size = max_request_size
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 检查请求大小
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            error_response = ErrorResponse(
                status=ResponseStatus.ERROR,
                message="Request too large",
                error=ErrorDetail(
                    error_code="REQUEST_TOO_LARGE",
                    error_type="ValidationError",
                    error_message=f"Request size exceeds maximum allowed size of {self.max_request_size} bytes"
                )
            )
            
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content=error_response.dict()
            )
        
        return await call_next(request)

def create_jwt_token(payload: Dict[str, Any], secret_key: str, 
                    expires_in: int = 3600, algorithm: str = "HS256") -> str:
    """创建JWT token
    
    Args:
        payload: token载荷
        secret_key: 密钥
        expires_in: 过期时间（秒）
        algorithm: 算法
        
    Returns:
        JWT token
    """
    # 添加过期时间
    payload["exp"] = datetime.utcnow() + timedelta(seconds=expires_in)
    payload["iat"] = datetime.utcnow()
    
    return jwt.encode(payload, secret_key, algorithm=algorithm)

def verify_jwt_token(token: str, secret_key: str, algorithm: str = "HS256") -> Dict[str, Any]:
    """验证JWT token
    
    Args:
        token: JWT token
        secret_key: 密钥
        algorithm: 算法
        
    Returns:
        token载荷
        
    Raises:
        jwt.InvalidTokenError: token无效
    """
    return jwt.decode(token, secret_key, algorithms=[algorithm])

def generate_api_key(client_name: str, secret: str) -> str:
    """生成API密钥
    
    Args:
        client_name: 客户端名称
        secret: 密钥
        
    Returns:
        API密钥
    """
    timestamp = str(int(time.time()))
    data = f"{client_name}:{timestamp}"
    signature = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    
    return f"{client_name}_{timestamp}_{signature[:16]}"

def create_request_signature(method: str, url: str, body: str, 
                           timestamp: str, secret: str) -> str:
    """创建请求签名
    
    Args:
        method: HTTP方法
        url: 请求URL
        body: 请求体
        timestamp: 时间戳
        secret: 密钥
        
    Returns:
        请求签名
    """
    data = f"{method}\n{url}\n{body}\n{timestamp}"
    return hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()