


### 大语言模型集成 MCP

#### OpenAI
OpenAI 本身并不直接支持 MCP（Model Context Protocol），但是可以通过几种方法将 MCP 服务和 OpenAI 模型结合使用。
1. 使用 MCP 客户端库来调用 MCP 服务器提供的工具，然后将这些工具的结果作为上下文提供给 OpenAI 模型。
2. 通过 OpenAI 的 Function Calling 功能​​：将 MCP 服务器提供的工具封装成 OpenAI 的 Function Calling 格式，然后通过 OpenAI API 调用。

* 通过 MCP 客户端库
步骤：
1. 使用 MCP Client 连接 MCP Server，获取可用的工具列表。
2. 当用户输入到来时，决定是否需要调用 MCP 工具。
3. 如果需要，调用 MCP 工具，并将结果作为上下文附加到用户输入中，然后发送给 OpenAI 模型。



* OpenAI Function Calling
OpenAI 的 Function Calling 允许您描述函数（工具）的签名，然后模型可以决定是否调用这些函数。您可以将 MCP 服务器提供的工具封装成 OpenAI 函数的形式。
步骤：
1. 将 MCP Server 的工具转换为 OpenAI 函数描述格式。
2. 在调用 OpenAI API 时，将这些函数描述传入。
3. 如果模型决定调用函数，则执行相应的 MCP 工具，并将结果返回给模型。





### MCP Client

#### Client With fastmcp
fastmcp.Client 提供了一个高级的异步接口，用于与任何模型上下文协议（MCP）服务器交互，无论该服务器是使用 FastMCP 构建的还是其他实现。它通过处理协议细节和连接管理简化了通信。


The FastMCP Client architecture separates the protocol logic (Client) from the connection mechanism (Transport)

* Client: Handles sending MCP requests (like tools/call, resources/read), receiving responses, and managing callbacks.
* Transport: Responsible for establishing and maintaining the connection to the server (e.g., via WebSockets, SSE, Stdio, or in-memory).





#### Client Methods

* list_tools(): Retrieves a list of tools available on the server.
```
tools = await client.list_tools()
# tools -> list[mcp.types.Tool]
```

* call_tool(name: str, arguments: dict[str, Any] | None = None, timeout: float | None = None, progress_handler: ProgressHandler | None = None): Executes a tool on the server.
```
result = await client.call_tool("add", {"a": 5, "b": 3})
# result -> list[mcp.types.TextContent | mcp.types.ImageContent | ...]
print(result[0].text) # Assuming TextContent, e.g., '8'

# With timeout (aborts if execution takes longer than 2 seconds)
result = await client.call_tool("long_running_task", {"param": "value"}, timeout=2.0)

# With progress handler (to track execution progress)
result = await client.call_tool(
    "long_running_task",
    {"param": "value"},
    progress_handler=my_progress_handler
)
```
1. Arguments are passed as a dictionary. FastMCP servers automatically handle JSON string parsing for complex types if needed.
2. Returns a list of content objects (usually TextContent or ImageContent).
3. The optional timeout parameter limits the maximum execution time (in seconds) for this specific call, overriding any client-level timeout.
4. The optional progress_handler parameter receives progress updates during execution, overriding any client-level progress handler.

* list_resources(): Retrieves a list of static resources
```
resources = await client.list_resources()
# resources -> list[mcp.types.Resource]
```

* list_resource_templates(): Retrieves a list of resource templates
```
templates = await client.list_resource_templates()
# templates -> list[mcp.types.ResourceTemplate]
```

* read_resource(uri: str | AnyUrl): Reads the content of a resource or a resolved template.
```
# Read a static resource
readme_content = await client.read_resource("file:///path/to/README.md")
# readme_content -> list[mcp.types.TextResourceContents | mcp.types.BlobResourceContents]
print(readme_content[0].text) # Assuming text

# Read a resource generated from a template
weather_content = await client.read_resource("data://weather/london")
print(weather_content[0].text) # Assuming text JSON
```

#### Example
```

import asyncio
from fastmcp import Client, FastMCP

# Example transports (more details in Transports page)
server_instance = FastMCP(name="TestServer") # In-memory server
http_url = "https://example.com/mcp"        # HTTP server URL
server_script = "my_mcp_server.py"         # Path to a Python server file

# Client automatically infers the transport type
client_in_memory = Client(server_instance)
client_http = Client(http_url)

client_stdio = Client(server_script)

print(client_in_memory.transport)
print(client_http.transport)
print(client_stdio.transport)

# Expected Output (types may vary slightly based on environment):
# <FastMCP(server='TestServer')>
# <StreamableHttp(url='https://example.com/mcp')>
# <PythonStdioTransport(command='python', args=['/path/to/your/my_mcp_server.py'])>


```

You can also initialize a client from an MCP configuration dictionary or MCPConfig file:
```
from fastmcp import Client

config = {
    "mcpServers": {
        "local": {"command": "python", "args": ["local_server.py"]},
        "remote": {"url": "https://example.com/mcp"},
    }
}

client_config = Client(config)
```


### refer
https://github.com/alejoair/mcp-open-client/blob/master/client.md

