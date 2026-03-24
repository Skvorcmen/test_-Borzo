import json
import os
from flask import Flask, render_template, request, jsonify, session
from functools import wraps
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "borzo_secret_key_change_in_production")

DATA_FILE = "data.json"

# Пароли для ролей
PASSWORDS = {"manager": "4007", "owner": "7004"}

# Начальные данные по умолчанию (ваш DEFAULT_DATA здесь...)
# ... (вставьте ваш DEFAULT_DATA)


def load_data():
    """Загрузка данных из файла"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_DATA.copy()


def save_data(data):
    """Сохранение данных в файл"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "role" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)

    return decorated


def require_owner(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "owner":
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)

    return decorated


@app.route("/")
def index():
    if "role" not in session:
        return render_template("index.html", initial_role=None)
    return render_template("index.html", initial_role=session.get("role"))


@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    role = data.get("role")
    password = data.get("password")
    if role in PASSWORDS and PASSWORDS[role] == password:
        session["role"] = role
        return jsonify({"success": True, "role": role})
    return jsonify({"success": False, "error": "Неверный пароль"}), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/check", methods=["GET"])
def check_auth():
    if "role" in session:
        return jsonify({"role": session["role"]})
    return jsonify({"role": None})


@app.route("/api/data", methods=["GET"])
def get_data():
    """Получение всех данных"""
    if "role" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = load_data()
    return jsonify(data)


@app.route("/api/data", methods=["POST"])
@require_auth
def save_data_route():
    """Сохранение данных"""
    new_data = request.json
    current_role = session.get("role")
    new_data["role"] = current_role
    save_data(new_data)
    return jsonify({"success": True})


@app.route("/api/proposal", methods=["POST"])
@require_auth
def add_proposal():
    if session.get("role") != "manager":
        return jsonify({"error": "Only managers can create proposals"}), 403
    data = load_data()
    proposal = request.json
    proposal["id"] = str(uuid.uuid4())
    data["proposals"].insert(0, proposal)
    save_data(data)
    return jsonify({"success": True, "id": proposal["id"]})


@app.route("/api/proposal/<proposal_id>", methods=["PUT"])
@require_owner
def update_proposal(proposal_id):
    data = load_data()
    for i, p in enumerate(data["proposals"]):
        if p.get("id") == proposal_id:
            updated = request.json
            updated["id"] = proposal_id
            data["proposals"][i] = updated
            save_data(data)
            return jsonify({"success": True})
    return jsonify({"error": "Proposal not found"}), 404


@app.route("/api/proposal/<proposal_id>", methods=["DELETE"])
@require_auth
def delete_proposal(proposal_id):
    data = load_data()
    for i, p in enumerate(data["proposals"]):
        if p.get("id") == proposal_id:
            data["proposals"].pop(i)
            save_data(data)
            return jsonify({"success": True})
    return jsonify({"error": "Proposal not found"}), 404


@app.route("/api/proposal/<proposal_id>/approve", methods=["POST"])
@require_owner
def approve_proposal(proposal_id):
    data = load_data()
    proposal = None
    proposal_index = None
    for i, p in enumerate(data["proposals"]):
        if p.get("id") == proposal_id:
            proposal = p
            proposal_index = i
            break
    if not proposal:
        return jsonify({"error": "Proposal not found"}), 404

    target_type = proposal.get("targetType")
    attachments = proposal.get("attachments", [])

    if target_type == "block":
        block_name = proposal.get("targetName")
        if block_name in data["blocks"]:
            if proposal.get("mode") == "replace" and isinstance(
                proposal.get("sourceIndex"), int
            ):
                messages = data["blocks"][block_name].get("messages", [])
                if proposal["sourceIndex"] < len(messages):
                    messages[proposal["sourceIndex"]] = {
                        "label": proposal.get("condition", ""),
                        "text": proposal.get("text", ""),
                        "attachments": attachments,
                    }
            else:
                data["blocks"][block_name]["messages"].append(
                    {
                        "label": proposal.get("condition", ""),
                        "text": proposal.get("text", ""),
                        "attachments": attachments,
                    }
                )
    elif target_type == "main-list":
        block_name = proposal.get("blockName")
        if block_name and block_name not in data["blocks"]:
            data["mainOrder"].append(block_name)
            data["blocks"][block_name] = {
                "kind": "main",
                "note": "",
                "hint": "",
                "messages": [
                    {
                        "label": proposal.get("condition", ""),
                        "text": proposal.get("text", ""),
                        "attachments": attachments,
                    }
                ],
            }
    elif target_type == "section":
        section_name = proposal.get("targetName")
        block_name = proposal.get("blockName")
        if block_name and section_name in data["sections"]:
            if block_name not in data["blocks"]:
                data["blocks"][block_name] = {
                    "kind": "side",
                    "note": "",
                    "hint": "",
                    "messages": [
                        {
                            "label": proposal.get("condition", ""),
                            "text": proposal.get("text", ""),
                            "attachments": attachments,
                        }
                    ],
                }
            if block_name not in data["sections"][section_name]:
                data["sections"][section_name].append(block_name)
    elif target_type == "new-section":
        section_name = proposal.get("sectionName")
        block_name = proposal.get("blockName")
        if section_name and section_name not in data["sections"]:
            data["sectionOrder"].append(section_name)
            data["sections"][section_name] = []
            if block_name:
                data["blocks"][block_name] = {
                    "kind": "side",
                    "note": "",
                    "hint": "",
                    "messages": [
                        {
                            "label": proposal.get("condition", ""),
                            "text": proposal.get("text", ""),
                            "attachments": attachments,
                        }
                    ],
                }
                data["sections"][section_name].append(block_name)

    data["proposals"].pop(proposal_index)
    save_data(data)
    return jsonify({"success": True})


@app.route("/api/proposal/<proposal_id>/reject", methods=["POST"])
@require_owner
def reject_proposal(proposal_id):
    data = load_data()
    comment = request.json.get("comment", "")
    for i, p in enumerate(data["proposals"]):
        if p.get("id") == proposal_id:
            if comment:
                if "managerMessages" not in data:
                    data["managerMessages"] = []
                data["managerMessages"].append(
                    {
                        "text": f'Предложение "{p.get("condition", "")}" отклонено. Причина: {comment}'
                    }
                )
            data["proposals"].pop(i)
            save_data(data)
            return jsonify({"success": True})
    return jsonify({"error": "Proposal not found"}), 404


@app.route("/api/messages", methods=["GET"])
@require_auth
def get_messages():
    if session.get("role") != "manager":
        return jsonify({"messages": []})
    data = load_data()
    messages = data.get("managerMessages", [])
    data["managerMessages"] = []
    save_data(data)
    return jsonify({"messages": messages})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)
