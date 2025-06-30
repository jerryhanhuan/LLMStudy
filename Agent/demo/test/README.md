


# AI Agent Demo

一个功能完整的AI智能代理演示项目，展示了如何构建一个具备工具调用、记忆管理、任务规划等高级功能的AI助手。

## 🌟 主要特性

### 🤖 核心功能
- **智能对话**: 基于大语言模型的自然语言交互
- **工具调用**: 支持多种内置和自定义工具
- **记忆管理**: 持久化对话历史和上下文记忆
- **任务规划**: 自动分解复杂任务并执行
- **流式响应**: 支持实时流式对话体验

### 🛠️ 内置工具
- **计算器**: 数学计算和表达式求值
- **天气查询**: 实时天气信息获取
- **邮件发送**: 自动化邮件发送功能
- **时间工具**: 时间查询和格式化
- **文件搜索**: 本地文件搜索和管理

### 🌐 Web API
- **RESTful API**: 完整的HTTP API接口
- **WebSocket**: 实时双向通信
- **认证授权**: JWT和API Key双重认证
- **速率限制**: 防止API滥用
- **CORS支持**: 跨域资源共享

### 📊 管理功能
- **会话管理**: 多会话并发处理
- **任务调度**: 异步任务执行和监控
- **系统监控**: 性能指标和健康检查
- **配置管理**: 灵活的配置系统

## 🚀 快速开始

### 环境要求
- Python 3.8+
- OpenAI API Key (或其他兼容的LLM API)

### 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd ai-agent-demo

# 安装依赖
pip install -r requirements.txt
```

### 配置设置

1. 复制环境变量模板：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，设置必要的配置：
```env
# LLM配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo

# 服务器配置
SERVER_HOST=localhost
SERVER_PORT=8000

# 数据库配置
DATABASE_PATH=data/agent.db
```

### 运行应用

#### Web服务器模式（推荐）
```bash
python main.py
```

访问 http://localhost:8000 查看API文档

#### 交互式命令行模式
```bash
python main.py --mode interactive
```

#### 其他运行选项
```bash
# 使用自定义配置文件
python main.py --config config.json

# 指定主机和端口
python main.py --host 0.0.0.0 --port 9000

# 启用调试模式
python main.py --debug

# 验证配置
python main.py --validate-config

# 显示当前配置
python main.py --show-config
```

## 📖 使用指南

### API接口

#### 基础对话
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下你自己",
    "session_id": "test_session"
  }'
```

#### 流式对话
```bash
curl -X POST "http://localhost:8000/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请计算 123 + 456",
    "session_id": "test_session"
  }'
```

#### 工具管理
```bash
# 获取可用工具列表
curl "http://localhost:8000/api/v1/tools"

# 执行特定工具
curl -X POST "http://localhost:8000/api/v1/tools/calculator/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "2 + 3 * 4"
  }'
```

#### 任务管理
```bash
# 创建任务
curl -X POST "http://localhost:8000/api/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "发送邮件给张三，内容是项目进度更新",
    "priority": "high"
  }'

# 获取任务列表
curl "http://localhost:8000/api/v1/tasks"

# 执行任务
curl -X POST "http://localhost:8000/api/v1/tasks/{task_id}/execute"
```

### 配置说明

项目支持多种配置方式，按优先级排序：
1. 命令行参数
2. 环境变量
3. 配置文件 (.json, .toml, .yaml)
4. 默认值

#### 主要配置项

```yaml
# LLM配置
llm:
  api_key: "your_api_key"
  api_base: "https://api.openai.com/v1"
  model: "gpt-3.5-turbo"
  max_tokens: 2048
  temperature: 0.7
  timeout: 30

# 服务器配置
server:
  host: "localhost"
  port: 8000
  debug: false
  reload: false

# Agent配置
agent:
  name: "AI Assistant"
  description: "智能助手"
  enable_tools: true
  enable_memory: true
  enable_planning: true
  max_history: 50
  tool_timeout: 30

# 工具配置
tools:
  calculator_enabled: true
  weather_enabled: true
  weather_api_key: "your_weather_api_key"
  email_enabled: true
  email_smtp_server: "smtp.gmail.com"
  email_smtp_port: 587
  time_enabled: true
  file_search_enabled: true

# 记忆配置
memory:
  storage_type: "sqlite"
  database_path: "data/memory.db"
  max_history: 100

# 日志配置
logging:
  level: "INFO"
  file: true
  file_path: "logs/agent.log"
  console: true
  max_size: "10MB"
  backup_count: 5
```
- 技术文档生成

### 4. 学习伙伴
**用例描述**: 作为智能学习助手，提供个性化的学习指导。

**特色功能**:
- 知识点解释和答疑
- 学习计划制定
- 练习题生成
- 学习进度跟踪

## 🛠️ 技术架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   用户界面层     │    │   Agent核心层    │    │   工具服务层     │
│                │    │                │    │                │
│ • Web界面      │◄──►│ • 意图理解      │◄──►│ • API调用      │
│ • CLI工具      │    │ • 任务规划      │    │ • 数据库操作    │
│ • API接口      │    │ • 执行引擎      │    │ • 文件处理      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   数据存储层     │
                    │                │
                    │ • 对话历史      │
                    │ • 任务状态      │
                    │ • 用户配置      │
                    └─────────────────┘
```

## 📦 安装配置

### 环境要求
- Python 3.8+
- Node.js 16+ (如需Web界面)
- 足够的内存和存储空间

### 快速开始

1. **克隆项目**
```bash
git clone <repository-url>
cd AI-Agent-Demo
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑.env文件，填入必要的API密钥和配置
```

4. **启动服务**
```bash
python main.py
```

### 配置说明

在`.env`文件中配置以下参数：

```env
# AI模型配置
OPENAI_API_KEY=your_openai_api_key
MODEL_NAME=gpt-4

# 数据库配置
DATABASE_URL=sqlite:///agent.db

# 服务配置
SERVER_HOST=localhost
SERVER_PORT=8000

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/agent.log
```

## 🎮 使用指南

### 基础使用

1. **启动Agent**
```python
from agent import AIAgent

# 初始化Agent
agent = AIAgent(config_file="config.yaml")

# 开始对话
response = agent.chat("你好，请帮我分析一下今天的股票市场")
print(response)
```

2. **自定义工具**
```python
# 注册自定义工具
@agent.tool
def custom_calculator(expression: str) -> float:
    """计算数学表达式"""
    return eval(expression)

# 使用工具
result = agent.chat("帮我计算 (123 + 456) * 789")
```

### 高级功能

#### 1. 任务链式执行
```python
tasks = [
    "查询当前天气",
    "根据天气情况推荐穿衣建议",
    "生成今日出行计划"
]

result = agent.execute_task_chain(tasks)
```

#### 2. 上下文管理
```python
# 保存对话上下文
agent.save_context("conversation_1")

# 加载历史上下文
agent.load_context("conversation_1")
```

#### 3. 插件系统
```python
# 加载插件
agent.load_plugin("weather_plugin")
agent.load_plugin("email_plugin")

# 查看可用工具
print(agent.list_tools())
```

### API接口使用

#### RESTful API

```bash
# 发送消息
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，AI助手"}'

# 获取对话历史
curl http://localhost:8000/api/history

# 执行特定任务
curl -X POST http://localhost:8000/api/task \
  -H "Content-Type: application/json" \
  -d '{"task": "分析数据文件", "params": {"file_path": "data.csv"}}'
```

#### WebSocket实时通信

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = function() {
    ws.send(JSON.stringify({
        type: 'chat',
        message: '开始新的对话'
    }));
};

ws.onmessage = function(event) {
    const response = JSON.parse(event.data);
    console.log('Agent回复:', response.message);
};
```

## 🔧 开发指南

### 项目结构
```
AI-Agent-Demo/
├── agent/                 # Agent核心模块
│   ├── __init__.py
│   ├── core.py           # 核心逻辑
│   ├── tools.py          # 工具管理
│   ├── memory.py         # 记忆管理
│   └── plugins/          # 插件目录
├── api/                  # API服务
│   ├── routes.py
│   └── websocket.py
├── web/                  # Web界面
│   ├── static/
│   └── templates/
├── tests/                # 测试文件
├── docs/                 # 文档
├── config.yaml           # 配置文件
├── requirements.txt      # 依赖列表
└── main.py              # 主程序入口
```

### 自定义开发

#### 1. 添加新工具
```python
from agent.tools import BaseTool

class WeatherTool(BaseTool):
    name = "weather"
    description = "获取天气信息"
    
    def execute(self, location: str) -> dict:
        # 实现天气查询逻辑
        return {"location": location, "temperature": "25°C"}
```

#### 2. 扩展Agent能力
```python
from agent.core import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_custom_tools()
    
    def custom_reasoning(self, query: str) -> str:
        # 自定义推理逻辑
        pass
```

## 📊 性能监控

### 指标监控
- 响应时间统计
- 任务成功率
- 资源使用情况
- 错误率分析

### 日志分析
```bash
# 查看实时日志
tail -f logs/agent.log

# 分析错误日志
grep "ERROR" logs/agent.log | tail -20
```

## 🔒 安全考虑

- **输入验证**: 严格验证用户输入，防止注入攻击
- **权限控制**: 基于角色的访问控制机制
- **数据加密**: 敏感数据传输和存储加密
- **审计日志**: 完整的操作审计记录

## 🤝 贡献指南

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系我们

- 项目主页: [GitHub Repository](https://github.com/your-username/ai-agent-demo)
- 问题反馈: [Issues](https://github.com/your-username/ai-agent-demo/issues)
- 邮箱: your-email@example.com

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者和社区成员！

---

**注意**: 这是一个演示项目，请根据实际需求进行相应的修改和扩展。
