from fluvius_test.navis_app

# Custom AsyncClient with FluviusJSONEncoder
class FluviusAsyncClient(AsyncClient):
    """AsyncClient that uses FluviusJSONEncoder for JSON serialization"""

    async def request(self, method, url, **kwargs):
        # If json data is provided, serialize it with FluviusJSONEncoder
        if 'json' in kwargs:
            kwargs['content'] = json.dumps(kwargs.pop('json'), cls=FluviusJSONEncoder)
            kwargs['headers'] = kwargs.get('headers') or {}
            kwargs['headers'].setdefault('Content-Type', 'application/json')

        return await super().request(method, url, **kwargs)
