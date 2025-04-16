from .app import app
from .config import HOST, PORT, DEBUG

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)