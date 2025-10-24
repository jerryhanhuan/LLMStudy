# server.py
from fastmcp import FastMCP

mcp = FastMCP("Demo 🚀")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

if __name__ == "__main__":
    # 方式1：使用默认STDIO方式（推荐用于MCP客户端连接）
    # mcp.run()
    
    # 方式2：使用 FastMCP 2.0 的 streamable-http 传输方式
    print("启动 FastMCP HTTP 服务器...")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)



'''
uv pip install fastmcp --system

python3 ./mcp_http.py
'''