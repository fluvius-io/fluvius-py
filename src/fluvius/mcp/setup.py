def setup_mcp(app):
    from fastapi_mcp import FastApiMCP
    mcp = FastApiMCP(app)
    mcp.mount()
    return mcp
