import os
import json
import base64
import logging
import datetime
import anthropic
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

SYSTEM_PROMPT = """Ты — помощник проекта Prime Era. Это пространство для глубокой работы с собой.

Темы, с которыми ты работаешь:
- Нумерология: классическая, кармическая, китайская (Ба-Цзы, Ло-Шу)
- Здоровье тела и пространства, практики осознанности, Фэн-шуй
- Медитации: звуковые практики, программные установки (аффирмации), дыхательные техники
- Работа с тревогой и страхами
- Личные границы
- Ценности и самопознание
- Успех и проектирование жизни
- Архитектура отношений

Отвечай тепло, поддерживающе, на русском языке. Будь конкретен и полезен.
Если человек хочет записаться на консультацию — направляй его к @prime_era_coach.
Не придумывай услуги, которых нет в списке выше."""

# ──────────────────────────────────────────────
# Тексты разделов
# ──────────────────────────────────────────────

SECTIONS = {
    "numerology": {
        "title": "🔢 Нумерология",
        "text": (
            "В *Prime Era* мы работаем с тремя системами нумерологии:\n\n"
            "✦ *Классическая нумерология* — числа имени и даты рождения раскрывают "
            "вашу личность, таланты и жизненный путь.\n\n"
            "✦ *Кармическая нумерология* — выявляет уроки прошлых жизней, "
            "«долги» и задачи, которые душа пришла решить в этом воплощении.\n\n"
            "✦ *Китайская нумерология (Ба-Цзы / Ло-Шу)* — анализирует энергетическую "
            "матрицу человека и периоды удачи через призму пяти стихий.\n\n"
            "Выберите направление или запишитесь на консультацию 👇"
        ),
        "buttons": [
            [("🔢 Классическая", "num_classic"), ("🌀 Кармическая", "num_karmic")],
            [("☯️ Китайская", "num_chinese")],
            [("📅 Записаться на консультацию", "book")],
            [("◀️ Назад", "main_menu")],
        ],
    },
    "num_classic": {
        "title": "🔢 Классическая нумерология",
        "text": (
            "Классическая нумерология изучает *число жизненного пути*, "
            "число судьбы, число души и другие коды вашей личности.\n\n"
            "Каждое число от 1 до 9 (и мастер-числа 11, 22, 33) несёт "
            "уникальный архетип и программу развития.\n\n"
            "💡 *Что вы узнаете:*\n"
            "• Ваши сильные стороны и природные таланты\n"
            "• Зоны роста и повторяющиеся паттерны\n"
            "• Благоприятные циклы и периоды жизни\n\n"
            "Хотите узнать своё число жизненного пути? Напишите дату рождения "
            "в формате ДД.ММ.ГГГГ — и я посчитаю!"
        ),
        "buttons": [
            [("📅 Записаться на консультацию", "book")],
            [("◀️ Назад к нумерологии", "numerology")],
        ],
    },
    "num_karmic": {
        "title": "🌀 Кармическая нумерология",
        "text": (
            "Кармическая нумерология работает с *«долгами»* и *«уроками»* души.\n\n"
            "Через числа мы видим:\n"
            "• Какие качества были утрачены или не развиты в прошлых жизнях\n"
            "• Что мешает двигаться вперёд (кармические хвосты)\n"
            "• Какие ситуации будут повторяться, пока урок не пройден\n\n"
            "🔑 *Кармическая карта* помогает:\n"
            "— Снять внутренние блоки\n"
            "— Понять повторяющиеся сценарии в отношениях и деньгах\n"
            "— Выйти на свой истинный путь\n\n"
            "Запишитесь на разбор кармической карты 👇"
        ),
        "buttons": [
            [("📅 Записаться на консультацию", "book")],
            [("◀️ Назад к нумерологии", "numerology")],
        ],
    },
    "num_chinese": {
        "title": "☯️ Китайская нумерология",
        "text": (
            "Китайская нумерология (Ло-Шу и Ба-Цзы) — это древняя система, "
            "основанная на *пяти стихиях* (огонь, вода, земля, металл, дерево).\n\n"
            "📊 *Матрица Ло-Шу* показывает:\n"
            "• Ваш врождённый потенциал и энергетические ресурсы\n"
            "• Отсутствующие числа — зоны для проработки\n"
            "• Связь с пространством, временем и судьбой\n\n"
            "🌿 *Ба-Цзы (Четыре столпа судьбы)* — карта жизни по дате и времени "
            "рождения, позволяет планировать карьеру, отношения и здоровье "
            "в гармонии с природными циклами."
        ),
        "buttons": [
            [("📅 Записаться на консультацию", "book")],
            [("◀️ Назад к нумерологии", "numerology")],
        ],
    },
    "health": {
        "title": "💚 Здоровье тела и пространства",
        "text": (
            "В *Prime Era* здоровье рассматривается как единство трёх уровней:\n\n"
            "🧘 *Тело* — физическое здоровье через практики осознанности, "
            "дыхательные техники, работу с телесными зажимами.\n\n"
            "🏠 *Пространство* — ваш дом и рабочее место влияют на ваше состояние. "
            "Мы работаем с энергетикой пространства через принципы Фэн-шуй "
            "и осознанного дизайна.\n\n"
            "🌱 *Энергия* — восстановление ресурсного состояния, работа "
            "с жизненной силой и внутренними ритмами.\n\n"
            "Выберите направление 👇"
        ),
        "buttons": [
            [("🧘 Практики для тела", "health_body"), ("🏠 Пространство", "health_space")],
            [("📅 Записаться на консультацию", "book")],
            [("◀️ Назад", "main_menu")],
        ],
    },
    "health_body": {
        "title": "🧘 Практики для тела",
        "text": (
            "Тело — это не просто физическая оболочка. Оно хранит все ваши "
            "эмоции, страхи и блоки.\n\n"
            "🌀 *Что входит в работу с телом:*\n"
            "• Дыхательные практики (пранаяма, коробочное дыхание, 4-7-8)\n"
            "• Телесное сканирование и осознанность\n"
            "• Работа с зажимами и хроническим напряжением\n"
            "• Практики заземления и центрирования\n\n"
            "Регулярная работа с телом снижает тревогу, улучшает сон "
            "и повышает уровень энергии. 🌿"
        ),
        "buttons": [
            [("📅 Записаться на консультацию", "book")],
            [("◀️ Назад", "health")],
        ],
    },
    "health_space": {
        "title": "🏠 Здоровье пространства",
        "text": (
            "Ваше пространство — это отражение вашего внутреннего состояния.\n\n"
            "🔑 *Принципы здорового пространства:*\n"
            "• Энергетическая чистка и расстановка мебели по Фэн-шуй\n"
            "• Зонирование по сферам жизни\n"
            "• Ароматы, звуки и свет как инструменты трансформации\n"
            "• Создание «якорей» для ресурсных состояний\n\n"
            "🏡 Осознанно обустроенное пространство поддерживает ваши цели "
            "и наполняет энергией каждый день."
        ),
        "buttons": [
            [("📅 Записаться на консультацию", "book")],
            [("◀️ Назад", "health")],
        ],
    },
    "meditation": {
        "title": "🧘‍♀️ Медитации и практики",
        "text": (
            "В *Prime Era* медитация — это не просто «сидеть тихо». "
            "Это *инструмент программирования* вашей реальности.\n\n"
            "🌟 *Направления:*\n\n"
            "🔊 *Звуковые практики* — поющие чаши, бинауральные ритмы, "
            "мантры. Звук воздействует напрямую на подсознание и нервную систему.\n\n"
            "💫 *Программные установки* — медитации с аффирмациями и "
            "визуализациями для перепрограммирования ограничивающих убеждений.\n\n"
            "🌬️ *Дыхательные практики* — техники для быстрого выхода "
            "из стресса и глубокого расслабления.\n\n"
            "🎯 *Медитации на цели* — работа с намерением, притяжение "
            "желаемого через осознанную практику."
        ),
        "buttons": [
            [("🔊 Звуковые практики", "sound"), ("💫 Установки", "affirmations")],
            [("📅 Записаться на консультацию", "book")],
            [("◀️ Назад", "main_menu")],
        ],
    },
    "sound": {
        "title": "🔊 Звуковые практики",
        "text": (
            "Звук — один из древнейших инструментов исцеления и трансформации.\n\n"
            "🎵 *Что используется в практиках:*\n"
            "• *Поющие чаши* (тибетские и кварцевые) — расслабление, "
            "гармонизация чакр, снятие тревоги\n"
            "• *Бинауральные ритмы* — специальные частоты для разных состояний: "
            "альфа (спокойствие), тета (глубокая медитация), дельта (сон)\n"
            "• *Мантры и звуки природы* — перепрограммирование через повторение\n"
            "• *Голосовые практики* — работа с собственным голосом как "
            "инструментом самоисцеления\n\n"
            "🌿 Регулярные звуковые практики снижают кортизол (гормон стресса) "
            "и улучшают качество сна."
        ),
        "buttons": [
            [("📅 Записаться на практику", "book")],
            [("◀️ Назад", "meditation")],
        ],
    },
    "affirmations": {
        "title": "💫 Программные установки",
        "text": (
            "Программные установки — это *осознанное перепрограммирование* "
            "подсознательных убеждений, которые управляют вашей жизнью.\n\n"
            "🧠 *Как это работает:*\n"
            "Подсознание не отличает реальное от воображаемого. "
            "Через повторение правильно составленных установок в состоянии "
            "расслабления мы «переписываем» ограничивающие программы.\n\n"
            "✨ *Темы установок в Prime Era:*\n"
            "• Деньги и изобилие\n"
            "• Отношения и любовь к себе\n"
            "• Здоровье и тело\n"
            "• Уверенность и успех\n"
            "• Снятие тревоги и страхов\n\n"
            "Запишитесь на индивидуальный сеанс для создания "
            "ваших персональных установок 👇"
        ),
        "buttons": [
            [("📅 Записаться на сеанс", "book")],
            [("◀️ Назад", "meditation")],
        ],
    },
    "anxiety": {
        "title": "🌊 Работа с тревогой",
        "text": (
            "Тревога — это сигнал, а не враг. В *Prime Era* мы учим "
            "слышать этот сигнал и работать с его причиной.\n\n"
            "🔍 *Что стоит за тревогой:*\n"
            "• Нарушение личных границ (своих или чужих)\n"
            "• Непроработанные страхи и убеждения\n"
            "• Жизнь «не своей» жизнью (против ценностей)\n"
            "• Накопленный стресс в теле\n\n"
            "🛠️ *Инструменты работы с тревогой:*\n"
            "✓ Дыхательные техники для быстрой помощи\n"
            "✓ Телесные практики для снятия напряжения\n"
            "✓ Работа с мыслями и убеждениями\n"
            "✓ Звуковые медитации\n"
            "✓ Нумерологический анализ (почему тревога приходит именно к вам)\n\n"
            "💛 Вы не одиноки в этом. Давайте разберём вместе."
        ),
        "buttons": [
            [("📅 Записаться на консультацию", "book")],
            [("🛡️ Мои границы", "boundaries")],
            [("◀️ Назад", "main_menu")],
        ],
    },
    "boundaries": {
        "title": "🛡️ Работа с границами",
        "text": (
            "Личные границы — это не стены. Это *правила*, которые говорят "
            "миру, как с вами можно обращаться, а как нельзя.\n\n"
            "🔑 *Признаки нарушенных границ:*\n"
            "• Вы часто говорите «да», когда хотите сказать «нет»\n"
            "• Чувствуете опустошённость после общения с людьми\n"
            "• Берёте на себя ответственность за чужие эмоции\n"
            "• Боитесь разочаровать или обидеть\n"
            "• Тревога нарастает в отношениях\n\n"
            "🌱 *Работа с границами в Prime Era:*\n"
            "— Осознание своих ценностей (без них границы не работают)\n"
            "— Практики «Нет без вины»\n"
            "— Нумерологический анализ паттернов в отношениях\n"
            "— Телесные практики для ощущения своих границ\n\n"
            "Здоровые границы = здоровые отношения = ваша жизнь 💛"
        ),
        "buttons": [
            [("📅 Записаться на консультацию", "book")],
            [("◀️ Назад", "main_menu")],
        ],
    },
    "success": {
        "title": "🌟 Успех и проектирование жизни",
        "text": (
            "В *Prime Era* успех — это не точка назначения, "
            "а *способ двигаться* в гармонии со своей природой.\n\n"
            "🗺️ *Проектирование жизни включает:*\n\n"
            "🔢 *Нумерологическая карта* — ваш природный потенциал "
            "и благоприятные направления\n\n"
            "💡 *Ценности* — без понимания своих истинных ценностей "
            "любой успех будет ощущаться пустым\n\n"
            "🎯 *Система целей* — постановка целей в гармонии "
            "с вашим типом личности и жизненным циклом\n\n"
            "🔄 *Ресурсное состояние* — работа с энергией, "
            "чтобы двигаться к целям без выгорания\n\n"
            "🏡 *Пространство успеха* — как обустроить среду, "
            "которая поддерживает ваши цели\n\n"
            "Готовы спроектировать свой успех? 🚀"
        ),
        "buttons": [
            [("📅 Записаться на консультацию", "book")],
            [("◀️ Назад", "main_menu")],
        ],
    },
    "values": {
        "title": "💎 Мои ценности",
        "text": (
            "Ценности — это *компас* вашей жизни. Когда вы живёте "
            "в соответствии со своими ценностями — есть энергия, смысл и радость. "
            "Когда против них — появляются тревога, пустота и усталость.\n\n"
            "🔍 *Как мы работаем с ценностями:*\n\n"
            "1️⃣ *Диагностика* — выявление истинных (а не навязанных) ценностей\n\n"
            "2️⃣ *Конфликт ценностей* — часто внутренние противоречия "
            "вызваны тем, что две важные ценности противоречат друг другу\n\n"
            "3️⃣ *Иерархия* — расстановка ценностей по приоритету\n\n"
            "4️⃣ *Интеграция* — как выстроить жизнь, карьеру и отношения "
            "вокруг своих ценностей\n\n"
            "💡 *Нумерология помогает* подтвердить ваши ценности через числа "
            "имени и даты рождения — это мощный инструмент самопознания."
        ),
        "buttons": [
            [("📅 Записаться на консультацию", "book")],
            [("◀️ Назад", "main_menu")],
        ],
    },
    "relationships": {
        "title": "💞 Архитектура отношений",
        "text": (
            "Отношения — это не случайность. Это *архитектура*, "
            "которую вы строите осознанно или бессознательно.\n\n"
            "В *Prime Era* мы исследуем отношения на нескольких уровнях:\n\n"
            "🔢 *Нумерология совместимости* — числа партнёров, "
            "кармические связи, уроки, которые вы проходите друг через друга.\n\n"
            "🪞 *Отношения с собой* — фундамент всего. Как вы относитесь к себе — "
            "так и другие будут относиться к вам. Работаем с самооценкой, "
            "любовью к себе и внутренним критиком.\n\n"
            "🛡️ *Границы в отношениях* — умение быть близким и при этом "
            "оставаться собой.\n\n"
            "🌀 *Кармические паттерны* — повторяющиеся сценарии в отношениях "
            "и как из них выйти.\n\n"
            "💑 *Проектирование отношений* — какие отношения вы хотите создать "
            "и что для этого нужно изменить в себе."
        ),
        "buttons": [
            [("🔢 Нумерология совместимости", "num_karmic"), ("🛡️ Границы", "boundaries")],
            [("📅 Записаться на консультацию", "book")],
            [("◀️ Назад", "main_menu")],
        ],
    },
    "book": {
        "title": "📅 Записаться на консультацию",
        "text": (
            "Отлично! Вы делаете важный шаг к себе. 🌟\n\n"
            "Для записи на консультацию, пожалуйста, напишите:\n\n"
            "1️⃣ Ваше имя\n"
            "2️⃣ Какая тема вас интересует (нумерология, тревога, границы и т.д.)\n"
            "3️⃣ Удобное время для связи\n\n"
            "Наш специалист свяжется с вами в ближайшее время 💛\n\n"
            "_Или напишите напрямую_ 👉 @prime_era_coach"
        ),
        "buttons": [
            [("◀️ На главную", "main_menu")],
        ],
    },
}

# ──────────────────────────────────────────────
# Главное меню
# ──────────────────────────────────────────────

MAIN_MENU_TEXT = (
    "✨ *Добро пожаловать в Prime Era* ✨\n\n"
    "Это пространство для глубокой работы с собой:\n"
    "познание своих ценностей, нумерология, здоровье тела и пространства, "
    "медитации, работа с тревогой и границами, проектирование успешной жизни.\n\n"
    "Выберите направление, которое вас интересует 👇"
)

MAIN_MENU_BUTTONS = [
    [
        InlineKeyboardButton("🔢 Нумерология", callback_data="numerology"),
        InlineKeyboardButton("💎 Мои ценности", callback_data="values"),
    ],
    [
        InlineKeyboardButton("💚 Здоровье тела и пространства", callback_data="health"),
    ],
    [
        InlineKeyboardButton("🧘‍♀️ Медитации и практики", callback_data="meditation"),
    ],
    [
        InlineKeyboardButton("🌊 Работа с тревогой", callback_data="anxiety"),
        InlineKeyboardButton("🛡️ Мои границы", callback_data="boundaries"),
    ],
    [
        InlineKeyboardButton("🌟 Успех и проектирование жизни", callback_data="success"),
    ],
    [
        InlineKeyboardButton("💞 Архитектура отношений", callback_data="relationships"),
    ],
    [
        InlineKeyboardButton("📅 Записаться на консультацию", callback_data="book"),
    ],
]


# ──────────────────────────────────────────────
# Хранилище заметок (в памяти)
# ──────────────────────────────────────────────

_notes: dict[int, list[str]] = {}

# ──────────────────────────────────────────────
# Tool-функции (вызываются через Claude tool use)
# ──────────────────────────────────────────────

def calculate(expression: str) -> str:
    """Безопасное вычисление математического выражения."""
    try:
        allowed = set("0123456789+-*/().% ")
        if not all(c in allowed for c in expression):
            return "Ошибка: недопустимые символы в выражении."
        result = eval(expression, {"__builtins__": {}})
        return str(result)
    except Exception as e:
        return f"Ошибка вычисления: {e}"


def save_note(user_id: int, note: str) -> str:
    """Сохранить заметку для пользователя."""
    _notes.setdefault(user_id, []).append(note)
    idx = len(_notes[user_id])
    return f"Заметка #{idx} сохранена: «{note}»"


def list_notes(user_id: int) -> str:
    """Вернуть список заметок пользователя."""
    notes = _notes.get(user_id, [])
    if not notes:
        return "У вас пока нет сохранённых заметок."
    lines = [f"{i+1}. {n}" for i, n in enumerate(notes)]
    return "Ваши заметки:\n" + "\n".join(lines)


def delete_note(user_id: int, index: int) -> str:
    """Удалить заметку по номеру (1-based)."""
    notes = _notes.get(user_id, [])
    if not notes:
        return "Нет заметок для удаления."
    if index < 1 or index > len(notes):
        return f"Неверный номер заметки. Всего заметок: {len(notes)}."
    removed = notes.pop(index - 1)
    return f"Заметка #{index} удалена: «{removed}»"


def get_datetime() -> str:
    """Вернуть текущую дату и время."""
    now = datetime.datetime.now()
    return now.strftime("Сегодня %d.%m.%Y, %H:%M")


def read_url(url: str) -> str:
    """Вернуть заглушку: бот не загружает URL в рантайме."""
    return f"Чтение URL в данной версии не поддерживается: {url}"


# Описание инструментов для Claude API
TOOLS = [
    {
        "name": "calculate",
        "description": "Вычислить математическое выражение. Принимает строку с арифметикой.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Математическое выражение, например '2 + 2 * 3'"}
            },
            "required": ["expression"],
        },
    },
    {
        "name": "save_note",
        "description": "Сохранить заметку для пользователя.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {"type": "string", "description": "Текст заметки"}
            },
            "required": ["note"],
        },
    },
    {
        "name": "list_notes",
        "description": "Показать все заметки пользователя.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "delete_note",
        "description": "Удалить заметку пользователя по номеру.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "description": "Номер заметки (с 1)"}
            },
            "required": ["index"],
        },
    },
    {
        "name": "get_datetime",
        "description": "Получить текущую дату и время.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "read_url",
        "description": "Прочитать содержимое URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Адрес страницы для чтения"}
            },
            "required": ["url"],
        },
    },
]


def _run_tool(name: str, tool_input: dict, user_id: int) -> str:
    """Диспетчер вызова tool-функций."""
    if name == "calculate":
        return calculate(tool_input["expression"])
    if name == "save_note":
        return save_note(user_id, tool_input["note"])
    if name == "list_notes":
        return list_notes(user_id)
    if name == "delete_note":
        return delete_note(user_id, tool_input["index"])
    if name == "get_datetime":
        return get_datetime()
    if name == "read_url":
        return read_url(tool_input["url"])
    return f"Неизвестный инструмент: {name}"


def build_keyboard(buttons_config: list) -> InlineKeyboardMarkup:
    keyboard = []
    for row in buttons_config:
        keyboard.append([InlineKeyboardButton(label, callback_data=data) for label, data in row])
    return InlineKeyboardMarkup(keyboard)


def ask_claude(user_message: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text


def ask_claude_with_tools(user_message: str, user_id: int) -> str:
    """Отправить сообщение Claude с поддержкой tool use. Выполняет цикл tool use."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _run_tool(block.name, block.input, user_id)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "Не удалось получить ответ."


def ask_claude_vision(image_bytes: bytes, mime_type: str, caption: str = "") -> str:
    """Отправить изображение в Claude Vision и получить описание/анализ."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": image_data,
            },
        }
    ]
    if caption:
        content.append({"type": "text", "text": caption})
    else:
        content.append({"type": "text", "text": "Опиши это изображение в контексте проекта Prime Era (нумерология, самопознание, здоровье, медитации)."})

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    return message.content[0].text


# ──────────────────────────────────────────────
# Обработчики команд
# ──────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        MAIN_MENU_TEXT,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(MAIN_MENU_BUTTONS),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "main_menu":
        await query.edit_message_text(
            MAIN_MENU_TEXT,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(MAIN_MENU_BUTTONS),
        )
        return

    section = SECTIONS.get(data)
    if not section:
        return

    keyboard = build_keyboard(section["buttons"])
    await query.edit_message_text(
        section["text"],
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    # Расчёт числа жизненного пути по дате рождения ДД.ММ.ГГГГ
    if len(text) == 10 and text[2] == "." and text[5] == ".":
        try:
            day, month, year = text.split(".")
            digits = day + month + year
            total = sum(int(d) for d in digits)
            while total > 9 and total not in (11, 22, 33):
                total = sum(int(d) for d in str(total))

            descriptions = {
                1: "Лидер и первопроходец. Вы рождены, чтобы прокладывать новые пути.",
                2: "Дипломат и миротворец. Ваша сила — в партнёрстве и чуткости.",
                3: "Творец и коммуникатор. Ваш дар — вдохновлять других своим творчеством.",
                4: "Строитель и практик. Вы создаёте прочные основы и ценности.",
                5: "Искатель свободы. Вы несёте перемены и новый опыт в этот мир.",
                6: "Хранитель и целитель. Ваша миссия — забота и создание гармонии.",
                7: "Мудрец и аналитик. Вы ищете глубинный смысл и истину.",
                8: "Строитель успеха. Вы умеете работать с материальным миром.",
                9: "Гуманист и учитель. Вы несёте мудрость и завершаете циклы.",
                11: "Мастер-интуит. Высший духовный потенциал и вдохновение для других.",
                22: "Мастер-строитель. Способность воплощать грандиозные идеи в жизнь.",
                33: "Мастер-учитель. Высшее служение любовью и мудростью.",
            }

            desc = descriptions.get(total, "Уникальное число!")
            await update.message.reply_text(
                f"🔢 *Ваше число жизненного пути: {total}*\n\n"
                f"✨ {desc}\n\n"
                f"Это лишь верхушка айсберга! Полный нумерологический разбор "
                f"откроет гораздо больше о вашей личности и жизненном пути.\n\n"
                f"Записаться на консультацию → напишите нам 👉 @prime_era_coach",
                parse_mode="Markdown",
            )
            return
        except Exception:
            pass

    # Для всех остальных сообщений — ответ через Claude AI с tool use
    if ANTHROPIC_API_KEY:
        try:
            await update.message.chat.send_action("typing")
            user_id = update.effective_user.id
            reply = ask_claude_with_tools(text, user_id)
            await update.message.reply_text(reply)
        except Exception as e:
            logging.error(f"Ошибка Claude API: {e}")
            await update.message.reply_text(
                "Привет! 👋 Нажмите /start, чтобы открыть меню Prime Era.\n\n"
                "Или введите дату рождения в формате ДД.ММ.ГГГГ — "
                "и я посчитаю ваше число жизненного пути 🔢"
            )
    else:
        await update.message.reply_text(
            "Привет! 👋 Нажмите /start, чтобы открыть меню Prime Era.\n\n"
            "Или введите дату рождения в формате ДД.ММ.ГГГГ — "
            "и я посчитаю ваше число жизненного пути 🔢"
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка фотографий через Claude Vision."""
    if not ANTHROPIC_API_KEY:
        await update.message.reply_text("API ключ не настроен. Обработка изображений недоступна.")
        return

    photo = update.message.photo[-1]  # наибольшее разрешение
    caption = update.message.caption or ""

    try:
        await update.message.chat.send_action("typing")
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        reply = ask_claude_vision(bytes(image_bytes), "image/jpeg", caption)
        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(f"Ошибка Claude Vision: {e}")
        await update.message.reply_text("Не удалось обработать изображение. Попробуйте ещё раз.")


# ──────────────────────────────────────────────
# Запуск
# ──────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ Agent bot started with tools")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
