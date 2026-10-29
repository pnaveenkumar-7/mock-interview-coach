from flask import Blueprint, jsonify

# Create Blueprint for student performance dashboard and metrics
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
def dashboard_index():
    """
    Placeholder endpoint for dashboard module.
    """
    return jsonify({"module": "dashboard", "status": "scaffold"})

