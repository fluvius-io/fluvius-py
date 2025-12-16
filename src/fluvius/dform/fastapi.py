from fluvius.dform.element import ElementModelRegistry


def setup_dform(app, base_path="/dform"):
    """
    Setup dform API endpoints on a FastAPI app.
    
    Args:
        app: FastAPI application instance
        base_path: Base path for all dform endpoints (default: /dform)
        
    Returns:
        The app with registered endpoints
    """
    from fluvius.fastapi.helper import uri
    
    def api(*paths, method=app.get, **kwargs):
        return method(uri(base_path, *paths), tags=["Data Form API"], **kwargs)
    
    @api("element-types")
    async def list_element_types():
        """List all registered element types"""
        return {
            "element_types": [
                {
                    "key": key,
                    "title": cls.Meta.title,
                    "description": cls.Meta.description,
                }
                for key, cls in ElementModelRegistry.items()
            ]
        }
    
    @api("element-schema/{element_key}")
    async def get_element_schema(element_key: str):
        """Get JSON schema for a specific element type"""
        # Registry.get raises NotFoundError if not found
        element_cls = ElementModelRegistry.get(element_key)
        
        # Return the Pydantic model's JSON schema
        return {
            "key": element_cls.Meta.key,
            "title": element_cls.Meta.title,
            "description": element_cls.Meta.description,
            "schema": element_cls.model_json_schema(),
        }
    
    return app
