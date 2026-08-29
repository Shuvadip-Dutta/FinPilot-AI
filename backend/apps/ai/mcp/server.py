from mcp.server import MCPServer


mcp = MCPServer(
    "FinPilot AI"
)


import apps.ai.mcp.tools.research

if __name__ == "__main__":
    mcp.run()