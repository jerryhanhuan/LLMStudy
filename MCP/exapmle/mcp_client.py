import asyncio
from fastmcp import Client



# Create a standard MCP configuration with multiple servers

config = {
    "mcpServers": {
        # A remote HTTP server
        "weather": {
            "url": "https://weather-api.example.com/mcp",
            "transport": "streamable-http"
        },
        # A local server running via stdio
        "assistant": {
            "command": "python",
            "args": ["./my_assistant_server.py"],
            "env": {"DEBUG": "true"}
        }
    }
}

# Create a client that connects to both servers
client = Client(config)


async def main():
    async with client:
        # Access tools from different servers with prefixes
        weather_data = await client.call_tool("weather_get_forecast", {"city": "London"})
        response = await client.call_tool("assistant_answer_question", {"question": "What's the capital of France?"})
        
        # Access resources with prefixed URIs
        weather_icons = await client.read_resource("weather://weather/icons/sunny")
        templates = await client.read_resource("resource://assistant/templates/list")
        
        print(f"Weather: {weather_data}")
        print(f"Assistant: {response}")

if __name__ == "__main__":
    asyncio.run(main())