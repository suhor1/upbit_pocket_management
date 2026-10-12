"""Flask 앱 팩토리."""

from __future__ import annotations

from pathlib import Path

from flask import Flask, render_template, url_for

from ..config import Settings
from ..errors import UpbitPocketError
from .routes import bp

# 이 중 하나가 static/ 에 있으면 네비 바닥의 브랜드 마크로 사용한다.
# 업비트 로고는 상표이므로 저장소에 포함하지 않고, 사용자가 직접 넣어준다.
LOGO_FILENAMES = (
    "upbit-logo.svg",
    "upbit-logo.png",
    "upbit-logo.webp",
    "logo.svg",
    "logo.png",
)


def find_brand_logo(static_dir: str | Path) -> str | None:
    static_path = Path(static_dir)
    for filename in LOGO_FILENAMES:
        if (static_path / filename).is_file():
            return filename
    return None


def create_app(settings: Settings | None = None, **overrides) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SETTINGS"] = settings or Settings.load()
    app.config["SECRET_KEY"] = app.config["SETTINGS"].secret_key
    app.config["JSON_AS_ASCII"] = False
    app.config.update(overrides)

    app.register_blueprint(bp)

    @app.context_processor
    def inject_brand():
        logo = find_brand_logo(app.static_folder)
        return {
            "brand_logo_url": url_for("static", filename=logo) if logo else None,
            "brand_title": "업비트 포켓 관리",
        }

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
