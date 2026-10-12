"""Flask 앱 팩토리."""

from __future__ import annotations

from flask import Flask, render_template

from ..config import Settings
from ..errors import UpbitPocketError
from .routes import bp


def create_app(settings: Settings | None = None, **overrides) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SETTINGS"] = settings or Settings.load()
    app.config["SECRET_KEY"] = app.config["SETTINGS"].secret_key
    app.config["JSON_AS_ASCII"] = False
    app.config.update(overrides)

    app.register_blueprint(bp)

    @app.errorhandler(UpbitPocketError)
    def handle_error(exc: UpbitPocketError):
        return render_template("error.html", message=str(exc)), 500

    @app.after_request
    def no_store(response):
        # 자산 정보가 캐시에 남지 않도록 막는다.
        if response.mimetype == "text/html":
            response.headers["Cache-Control"] = "no-store"
        return response

    return app
