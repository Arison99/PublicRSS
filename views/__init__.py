from flask import Blueprint

onboarding_bp = Blueprint("onboarding", __name__)
review_bp = Blueprint("review", __name__)
directory_bp = Blueprint("directory", __name__)

from . import onboarding, review, directory
