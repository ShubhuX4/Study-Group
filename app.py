"""
app.py  -  Flask backend of Study Group Finder (Unit V)
Run with:  python app.py
"""
from flask import Flask, jsonify, request, render_template, send_file

import study_group as sg
import analytics

app = Flask(__name__)


def error_response(message, status, errors=None):
    """Create a JSON error response with an HTTP status code."""
    body = {"success": False, "message": message}
    if errors:
        body["errors"] = errors
    return jsonify(body), status


# ---------------- Page ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- Groups API ----------------
@app.route("/api/groups", methods=["GET"])
def get_groups():
    """GET /api/groups?search=&subject=&mode=&timing=&available=true"""
    try:
        groups = sg.load_groups()
        groups = sg.search_groups(
            groups,
            request.args.get("search", ""),
            request.args.get("subject", ""),
            request.args.get("mode", ""),
            request.args.get("timing", ""),
        )
        if request.args.get("available") == "true":
            groups = list(sg.open_groups(groups))      # generator
        data = [g.to_api_dict() for g in groups]
        return jsonify({"success": True, "count": len(data), "groups": data}), 200
    except Exception as error:
        return error_response(f"Could not load groups: {error}", 500)


@app.route("/api/groups/<int:group_id>", methods=["GET"])
def get_group(group_id):
    try:
        group = sg.find_group(sg.load_groups(), group_id)
        return jsonify({"success": True, "group": group.to_api_dict()}), 200
    except sg.GroupNotFoundError as error:
        return error_response(str(error), 404)


@app.route("/api/groups", methods=["POST"])
def create_group():
    data = request.get_json(silent=True)          # read JSON sent by fetch()
    if not data:
        return error_response("Request body must be JSON.", 400)
    try:
        group = sg.create_group(data)
        return jsonify({"success": True, "message": "Study group created successfully!",
                        "group": group.to_api_dict()}), 201
    except sg.ValidationError as error:
        return error_response(str(error), 400, error.errors)
    except OSError as error:
        return error_response(str(error), 500)


@app.route("/api/groups/<int:group_id>", methods=["PUT"])
def update_group(group_id):
    """PUT /api/groups/<id>  with JSON body: creator "email" + the group fields"""
    data = request.get_json(silent=True)
    if not data or str(data.get("email", "")).strip() == "":
        return error_response("Creator email is required to edit a group.", 400)
    try:
        group = sg.update_group(group_id, data)
        return jsonify({"success": True, "message": "Group updated successfully!",
                        "group": group.to_api_dict()}), 200
    except sg.ValidationError as error:
        return error_response(str(error), 400, error.errors)
    except sg.GroupNotFoundError as error:
        return error_response(str(error), 404)
    except sg.NotCreatorError as error:
        return error_response(str(error), 403)
    except OSError as error:
        return error_response(str(error), 500)


@app.route("/api/groups/<int:group_id>/join", methods=["POST"])
def join_group(group_id):
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be JSON.", 400)
    try:
        group = sg.join_group(group_id, data)
        return jsonify({"success": True, "message": f"You joined '{group.name}'!",
                        "group": group.to_api_dict()}), 200
    except sg.ValidationError as error:
        return error_response(str(error), 400, error.errors)
    except sg.GroupNotFoundError as error:
        return error_response(str(error), 404)
    except sg.DuplicateRegistrationError as error:
        return error_response(str(error), 409)
    except sg.GroupFullError as error:
        return error_response(str(error), 409)
    except OSError as error:
        return error_response(str(error), 500)


@app.route("/api/groups/<int:group_id>/leave", methods=["POST"])
def leave_group(group_id):
    """POST /api/groups/<id>/leave  with JSON body {"email": "member@email"}"""
    data = request.get_json(silent=True)
    if not data:
        return error_response("Request body must be JSON.", 400)
    try:
        group = sg.leave_group(group_id, data)
        return jsonify({"success": True, "message": f"You left '{group.name}'.",
                        "group": group.to_api_dict()}), 200
    except sg.ValidationError as error:
        return error_response(str(error), 400, error.errors)
    except sg.GroupNotFoundError as error:
        return error_response(str(error), 404)
    except sg.NotMemberError as error:
        return error_response(str(error), 404)
    except sg.CreatorCannotLeaveError as error:
        return error_response(str(error), 403)
    except OSError as error:
        return error_response(str(error), 500)


@app.route("/api/groups/<int:group_id>", methods=["DELETE"])
def delete_group(group_id):
    """DELETE /api/groups/<id>  with JSON body {"email": "creator@email"}"""
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    if email == "":
        return error_response("Creator email is required to delete a group.", 400)
    try:
        group = sg.delete_group(group_id, email)
        return jsonify({"success": True, "message": f"Group '{group.name}' was deleted."}), 200
    except sg.GroupNotFoundError as error:
        return error_response(str(error), 404)
    except sg.NotCreatorError as error:
        return error_response(str(error), 403)
    except OSError as error:
        return error_response(str(error), 500)


@app.route("/api/my-groups", methods=["GET"])
def my_groups():
    """GET /api/my-groups?email=student@example.com"""
    email = request.args.get("email", "").strip()
    if email == "":
        return error_response("Query parameter 'email' is required.", 400)
    groups = sg.get_my_groups(email)
    return jsonify({"success": True, "count": len(groups), "groups": groups}), 200


@app.route("/api/subjects", methods=["GET"])
def get_subjects():
    """Lists used by the dropdowns in the frontend."""
    return jsonify({"subjects": list(sg.SUBJECTS), "modes": list(sg.MODES),
                    "timings": list(sg.TIMINGS), "day_types": list(sg.DAY_TYPES)}), 200


# ---------------- Analytics API ----------------
def groups_as_dicts():
    return [g.to_api_dict() for g in sg.load_groups()]


@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    stats = analytics.get_stats(groups_as_dicts(), sg.load_registrations())
    return jsonify({"success": True, "stats": stats}), 200


@app.route("/api/analytics/chart/<chart_type>", methods=["GET"])
def get_chart(chart_type):
    """chart_type: subjects | mode | registrations  -> returns a PNG image"""
    if chart_type not in analytics.CHART_FUNCTIONS:
        return error_response("Unknown chart type. Use subjects, mode or registrations.", 404)
    image = analytics.CHART_FUNCTIONS[chart_type](groups_as_dicts())
    return send_file(image, mimetype="image/png", max_age=0)


# ---------------- Generic error handlers ----------------
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith("/api/"):
        return error_response("Endpoint not found.", 404)
    return render_template("index.html"), 200


@app.errorhandler(405)
def method_not_allowed(error):
    return error_response("Method not allowed for this endpoint.", 405)


if __name__ == "__main__":
    app.run(debug=True)
