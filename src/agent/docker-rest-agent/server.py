import logging
from flask import Flask, request

from app.routes import register_routes
from app.utils import register_error_handlers


def create_app():
    app = Flask(__name__)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    @app.before_request
    def _log_request():
        try:
            payload = request.get_json(silent=True)
        except Exception:
            payload = None
        logging.info(
            "[agent] %s %s headers=%s body=%s",
            request.method,
            request.path,
            dict(request.headers),
            payload or request.form.to_dict() or {},
        )

    @app.after_request
    def _log_response(response):
        logging.info(
            "[agent] response %s %s status=%s",
            request.method,
            request.path,
            response.status,
        )
        return response

    register_error_handlers(app)
    register_routes(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
