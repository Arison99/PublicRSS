"""
PublicRSS MVP - AI-Assisted RSS Discovery Engine.
Flask MVT Application Entrypoint.
"""
import os
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from models.db import db, init_db
from models.feed import Feed
from views import onboarding_bp, review_bp, directory_bp
from views.directory import seed_initial_feeds


def create_app(test_config=None):
    app = Flask(__name__, static_folder="static", template_folder="templates")

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "publicrss-secure-session-key-dev-mode")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///publicrss.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if test_config:
        app.config.update(test_config)

    # Initialize SQLite Database
    init_db(app)

    # Register View Blueprints
    app.register_blueprint(directory_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(review_bp)

    # Ensure baseline feeds are seeded on fresh launch
    with app.app_context():
        if Feed.query.count() == 0:
            seed_initial_feeds()

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    # Run server-rendered Flask app on 0.0.0.0:3000
    app.run(host="0.0.0.0", port=port, debug=False)
