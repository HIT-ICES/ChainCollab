from flask import Flask

from app.routes import register_routes
from app.utils import register_error_handlers


def create_app():
    app = Flask(__name__)
    register_error_handlers(app)
    register_routes(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
