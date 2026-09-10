"""HTTP routes, grouped into blueprints and registered on the app."""
from __future__ import annotations

from flask import Flask

from .api import api_bp
from .pages import pages_bp


def register_routes(app: Flask) -> None:
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
