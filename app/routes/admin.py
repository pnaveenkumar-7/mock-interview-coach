from flask import Blueprint, render_template
from app.auth_utils import login_required, role_required

# Create Blueprint for Placement Officer / Admin features
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@role_required("admin")
def admin_index():
    """
    Placement Officer / Admin home dashboard.
    Restricted strictly to users with role='admin'.
    """
    return render_template("admin/index.html")
