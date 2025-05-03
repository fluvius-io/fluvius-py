from fastapi_mcp import FastApiMCP

def configure_mcp_server(app):
    mcp = FastApiMCP(app)
    mcp.mount()
    return mcp
