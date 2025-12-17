from fluvius.dform.element import ElementSchemaRegistry
from fluvius.error import NotFoundError


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
    
    @api("/element-types")
    async def list_element_types():
        """List all registered element types"""
        return {
            "element_types": [
                {
                    "key": key,
                    "name": cls.Meta.name,
                    "desc": cls.Meta.desc,
                }
                for key, cls in ElementSchemaRegistry.items()
            ]
        }
    
    @api("/element-schema/{element_key}")
    async def get_element_schema(element_key: str):
        """Get JSON schema for a specific element type"""
        try:
            element_cls = ElementSchemaRegistry.get(element_key)
        except KeyError:
            raise NotFoundError(
                "F00.301",
                f"Element type not found: {element_key}",
                None
            )
        
        # Return the Pydantic model's JSON schema
        return {
            "key": element_cls.Meta.key,
            "name": element_cls.Meta.name,
            "desc": element_cls.Meta.desc,
            "schema": element_cls.Model.model_json_schema(),
        }
    
    return app