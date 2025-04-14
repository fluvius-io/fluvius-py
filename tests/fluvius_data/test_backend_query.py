from fluvius.data.query import BackendQuery

def test_backend_query():
    t = BackendQuery(where=dict(), sort='hello')
    assert t.sort == ('hello', )
