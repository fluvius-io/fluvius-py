from fluvius.dform.element import ElementModelRegistry
from fluvius.dform.form import FormModelRegistry


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
    
    # Element type endpoints
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
    
    # Form type endpoints
    @api("form-types")
    async def list_form_types():
        """List all registered form types"""
        return {
            "form_types": [
                {
                    "key": key,
                    "name": cls.Meta.name,
                    "desc": getattr(cls.Meta, 'desc', None),
                }
                for key, cls in FormModelRegistry.items()
            ]
        }
    
    @api("form-schema/{form_key}")
    async def get_form_schema(form_key: str):
        """Get JSON schema for a specific form type"""
        # Registry.get raises NotFoundError if not found
        form_cls = FormModelRegistry.get(form_key)
        
        # Return the form schema
        return {
            "key": form_cls.Meta.key,
            "name": form_cls.Meta.name,
            "desc": getattr(form_cls.Meta, 'desc', None),
            "schema": form_cls.model_json_schema(),
        }
    
    return app
