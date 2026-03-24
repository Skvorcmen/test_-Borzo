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

# Начальные данные по умолчанию
DEFAULT_DATA = {
    "role": "manager",
    "currentBlock": "Входящий старт",
    "lastMain": "Входящий старт",
    "mainOrder": [
        "Входящий старт",
        "Выбор модели",
        "Размер и цвет",
        "Город клиента",
        "Доставка и оплата",
        "Финальное подтверждение",
    ],
    "sectionOrder": [
        "Вопросы клиентов",
        "Обработка возражений",
        "Пауза",
        "Закрытие клиента",
    ],
    "sections": {
        "Вопросы клиентов": [
            "Где посмотреть",
            "Разница моделей",
            "Нестандартный размер",
            "Другой цвет",
        ],
        "Обработка возражений": [
            "Дорого",
            "Сомнение в прочности",
            "Сомнение в качестве",
            "Доставка после 18:00",
        ],
        "Пауза": [
            "Подумаю / позже",
            "Молчание после фильтра",
            "Выбрал модель и пропал",
            "Пропал после ссылки на оплату",
        ],
        "Закрытие клиента": ["Дорого — закрытие", "Не сейчас"],
    },
    "blocks": {
        "Входящий старт": {
            "kind": "main",
            "note": "Если клиент сразу ушёл в уточняющий вопрос, после ответа его нужно вернуть в магистраль.",
            "hint": "",
            "messages": [
                {
                    "label": "Стандартный входящий",
                    "text": "Здравствуйте. Меня зовут Индира, менеджер BORZO.\n\nСейчас отправлю цены и краткое описание.",
                    "attachments": [],
                },
                {
                    "label": "Если клиент сразу спросил город",
                    "text": "Здравствуйте. Меня зовут Индира, менеджер BORZO.\n\nФабрика находится в Астане. Отправляем по всему Казахстану через Kaspi.\n\nСейчас отправлю цены и краткое описание.",
                    "attachments": [],
                },
                {
                    "label": "Шапка + прайс",
                    "text": "BORZO — дизайнерская консоль,\nкоторая станет украшением вашего интерьера.\n\nLUX:\n3 м — 310 000 ₸\n3,5 м — 335 000 ₸\n4 м — 360 000 ₸\n\nGEOMETRY (модель 2026, с подсветкой):\n3 м — 335 000 ₸\n3,5 м — 360 000 ₸\n4 м — 385 000 ₸",
                    "attachments": [],
                },
                {
                    "label": "Фильтр по сроку",
                    "text": "Мы изготавливаем столы партиями и не держим большой склад,\nпоэтому уточню — вы планируете покупку в ближайшее время?",
                    "attachments": [],
                },
            ],
        },
        "Выбор модели": {
            "kind": "main",
            "note": "",
            "hint": "После этого сообщения отправить фото моделей.",
            "messages": [
                {
                    "label": "Основное сообщение",
                    "text": "Какой вариант вам ближе — LUX или GEOMETRY?",
                    "attachments": [],
                }
            ],
        },
        "Размер и цвет": {
            "kind": "main",
            "note": "Если клиент перескочил к доставке или городу — вернуть его к выбору размера и цвета.",
            "hint": "",
            "messages": [
                {
                    "label": "Основное сообщение",
                    "text": "Отлично 👍\n\nУ наших столов есть стандартные размеры:\nВ сложенном виде консоль — 100×45×76 см\nВ разложенном формате доступны варианты — 3 м / 3,5 м / 4 м\n\nПодскажите размер и цвет? Уточню, доступен ли этот вариант сейчас.",
                    "attachments": [],
                }
            ],
        },
        "Город клиента": {
            "kind": "main",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Сообщение",
                    "text": "Ваш вариант доступен.\n\nПодскажите, с какого вы города?",
                    "attachments": [],
                }
            ],
        },
        "Доставка и оплата": {
            "kind": "main",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Если Астана",
                    "text": "По Астане доставка бесплатная.\n\nПодскажите ваш адрес и в какое время будет удобно принять доставку?",
                    "attachments": [],
                }
            ],
        },
        "Финальное подтверждение": {
            "kind": "main",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Подтверждение",
                    "text": "Подтверждаю:\n\n— модель\n— размер\n— цвет\n— город доставки\n— способ оплаты\n\nВсё верно?",
                    "attachments": [],
                }
            ],
        },
        "Где посмотреть": {
            "kind": "side",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Ответ",
                    "text": "Работаем в онлайн-формате напрямую от фабрики в Астане.\n\nЕсть подробные видеообзоры — отправить вам?",
                    "attachments": [],
                }
            ],
        },
        "Разница моделей": {
            "kind": "side",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Ответ",
                    "text": "Разница в дизайне и деталях исполнения.\n\nLUX — более классическая модель.\nGEOMETRY — сложная геометрия основания и подсветка.",
                    "attachments": [],
                }
            ],
        },
        "Нестандартный размер": {
            "kind": "side",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Ответ",
                    "text": "Мы работаем с фиксированными размерами. Индивидуальные размеры не изготавливаем.",
                    "attachments": [],
                }
            ],
        },
        "Другой цвет": {
            "kind": "side",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Ответ",
                    "text": "Мы работаем с утверждённой палитрой. Другие оттенки не производим.",
                    "attachments": [],
                }
            ],
        },
        "Дорого": {
            "kind": "side",
            "note": "После обработки возражения нужно вернуться туда, где менеджер был до ветки.",
            "hint": "",
            "messages": [
                {
                    "label": "Ответ",
                    "text": "Понимаю. Цена выше среднего, потому что конструкция и подход отличаются.",
                    "attachments": [],
                }
            ],
        },
        "Сомнение в прочности": {
            "kind": "side",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Ответ",
                    "text": "Конструкция тестировалась на нагрузку 200+ кг.",
                    "attachments": [],
                }
            ],
        },
        "Сомнение в качестве": {
            "kind": "side",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Ответ",
                    "text": "Если вдруг что-то не устроит — можно оформить возврат.",
                    "attachments": [],
                }
            ],
        },
        "Доставка после 18:00": {
            "kind": "side",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Ответ",
                    "text": "Да, мы можем согласовать доставку на вечернее время после 18:00.",
                    "attachments": [],
                }
            ],
        },
        "Подумаю / позже": {
            "kind": "side",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Ответ",
                    "text": "Поняла вас. Если есть вопросы — уточняйте, я всё подробно расскажу.",
                    "attachments": [],
                }
            ],
        },
        "Молчание после фильтра": {
            "kind": "side",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Ответ",
                    "text": "Подскажите, ваш запрос по столу ещё актуален?",
                    "attachments": [],
                }
            ],
        },
        "Выбрал модель и пропал": {
            "kind": "side",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Ответ",
                    "text": "Здравствуйте! Остались вопросы по столу или нужно уточнить детали заказа?",
                    "attachments": [],
                }
            ],
        },
        "Пропал после ссылки на оплату": {
            "kind": "side",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Ответ",
                    "text": "Если возникли вопросы по оплате или нужна помощь — напишите, помогу разобраться.",
                    "attachments": [],
                }
            ],
        },
        "Дорого — закрытие": {
            "kind": "side",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Закрытие",
                    "text": "Если вернётесь к вопросу позже — буду рада помочь.",
                    "attachments": [],
                }
            ],
        },
        "Не сейчас": {
            "kind": "side",
            "note": "",
            "hint": "",
            "messages": [
                {
                    "label": "Закрытие",
                    "text": "Если позже вопрос снова станет актуальным — напишите.",
                    "attachments": [],
                }
            ],
        },
    },
    "proposals": [],
    "managerMessages": [],
}


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


# ВАЖНО: ДОБАВЛЯЕМ GET МАРШРУТ
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
