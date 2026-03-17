from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from keyboards.reply import get_main_keyboard

router = Router()


# ─────────────────────────────────────────────
#  Данные предметов ОГЭ
# ─────────────────────────────────────────────

# Структура: callback_data → (название, список ресурсов [(текст, url), ...])
OGE_SUBJECTS: dict[str, tuple[str, list[tuple[str, str]]]] = {
    "oge_math": (
        "📐 Математика",
        [
            ("📖 Справочник Ященко (ФИПИ)", "https://fipi.ru/oge/otkrytyy-bank-zadaniy-oge#!/tab/151883967-3"),
            ("🧮 Тренажёр — mathb.in",       "https://mathb.in"),
            ("🎥 Видеоуроки — Борис Трушин",  "https://www.youtube.com/@trushin_math"),
            ("📝 Варианты 2025 — решу ОГЭ",   "https://math-oge.sdamgia.ru"),
        ],
    ),
    "oge_rus": (
        "✍️ Русский язык",
        [
            ("📖 Теория (ФИПИ)",              "https://fipi.ru/oge/otkrytyy-bank-zadaniy-oge#!/tab/151883967-1"),
            ("📝 Решу ОГЭ — варианты",        "https://rus-oge.sdamgia.ru"),
            ("📚 Справочник Баранова",         "https://www.labirint.ru/books/456789/"),
            ("🎥 Грамотей — YouTube",          "https://www.youtube.com/@gramotei"),
        ],
    ),
    "oge_social": (
        "🌍 Обществознание",
        [
            ("📖 Кодификатор ФИПИ",           "https://fipi.ru/oge/otkrytyy-bank-zadaniy-oge#!/tab/151883967-6"),
            ("📝 Решу ОГЭ — варианты",        "https://soc-oge.sdamgia.ru"),
            ("📚 Боголюбов — теория онлайн",  "https://uchebnikfree.com/page/obchestvoznanie_9"),
            ("🗂 Шпаргалки — 4ege.ru",         "https://4ege.ru/oge-obschestvoznanie/"),
        ],
    ),
    "oge_eng": (
        "🇬🇧 Английский язык",
        [
            ("📖 Банк заданий ФИПИ",          "https://fipi.ru/oge/otkrytyy-bank-zadaniy-oge#!/tab/151883967-8"),
            ("📝 Решу ОГЭ — варианты",        "https://en-oge.sdamgia.ru"),
            ("🎧 Аудирование — ФИПИ",         "https://oge.fipi.ru/"),
            ("📚 Wordwall — лексика",         "https://wordwall.net/ru"),
        ],
    ),
    "oge_inform": (
        "💻 Информатика",
        [
            ("📖 Банк заданий ФИПИ",          "https://fipi.ru/oge/otkrytyy-bank-zadaniy-oge#!/tab/151883967-9"),
            ("📝 Решу ОГЭ — варианты",        "https://inf-oge.sdamgia.ru"),
            ("🐍 Питон — py.checkio.org",     "https://py.checkio.org"),
            ("🎥 Видеоуроки — Поляков",       "https://www.youtube.com/@polyakov_kp"),
        ],
    ),
    "oge_bio": (
        "🧬 Биология",
        [
            ("📖 Банк заданий ФИПИ",          "https://fipi.ru/oge/otkrytyy-bank-zadaniy-oge#!/tab/151883967-4"),
            ("📝 Решу ОГЭ — варианты",        "https://bio-oge.sdamgia.ru"),
            ("📚 Пасечник — теория",          "https://uchebnikfree.com/page/biology_9"),
            ("🗂 Шпаргалки — 4ege.ru",         "https://4ege.ru/oge-biologiya/"),
        ],
    ),
    "oge_history": (
        "📜 История",
        [
            ("📖 Банк заданий ФИПИ",          "https://fipi.ru/oge/otkrytyy-bank-zadaniy-oge#!/tab/151883967-5"),
            ("📝 Решу ОГЭ — варианты",        "https://hist-oge.sdamgia.ru"),
            ("🗺 Карты и хронология",         "https://histrf.ru"),
            ("🎥 Алексей Костылёв — YouTube", "https://www.youtube.com/@kostylev_history"),
        ],
    ),
    "oge_phys": (
        "⚛️ Физика",
        [
            ("📖 Банк заданий ФИПИ",          "https://fipi.ru/oge/otkrytyy-bank-zadaniy-oge#!/tab/151883967-7"),
            ("📝 Решу ОГЭ — варианты",        "https://phys-oge.sdamgia.ru"),
            ("📚 Мякишев — теория онлайн",    "https://uchebnikfree.com/page/fizika_9"),
            ("🎥 Физика — Дмитрий Димитриев", "https://www.youtube.com/@dd_physics"),
        ],
    ),
}


# ─────────────────────────────────────────────
#  Клавиатуры
# ─────────────────────────────────────────────

def get_oge_subjects_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура выбора предмета ОГЭ."""
    buttons = [
        [
            InlineKeyboardButton(text="📐 Математика",    callback_data="oge_math"),
            InlineKeyboardButton(text="✍️ Русский язык",  callback_data="oge_rus"),
        ],
        [
            InlineKeyboardButton(text="🌍 Обществознание", callback_data="oge_social"),
            InlineKeyboardButton(text="🇬🇧 Английский",   callback_data="oge_eng"),
        ],
        [
            InlineKeyboardButton(text="💻 Информатика",   callback_data="oge_inform"),
            InlineKeyboardButton(text="🧬 Биология",      callback_data="oge_bio"),
        ],
        [
            InlineKeyboardButton(text="📜 История",       callback_data="oge_history"),
            InlineKeyboardButton(text="⚛️ Физика",        callback_data="oge_phys"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_subject_resources_keyboard(subject_key: str) -> InlineKeyboardMarkup:
    """Клавиатура с ресурсами для конкретного предмета."""
    _, resources = OGE_SUBJECTS[subject_key]

    link_buttons = [
        [InlineKeyboardButton(text=label, url=url)]
        for label, url in resources
    ]
    # Кнопка «назад» к списку предметов
    link_buttons.append([
        InlineKeyboardButton(text="◀️ Назад к предметам", callback_data="oge_back")
    ])
    return InlineKeyboardMarkup(inline_keyboard=link_buttons)


# ─────────────────────────────────────────────
#  Расписание звонков
# ─────────────────────────────────────────────

BELLS_SCHEDULE = """
🔔 <b>Расписание звонков</b>
<code>──────────────────────────</code>
<b>1 урок</b>  │  08:00 – 08:40
<b>2 урок</b>  │  08:50 – 09:30
<b>3 урок</b>  │  09:45 – 10:25
<b>4 урок</b>  │  10:45 – 11:25
<b>5 урок</b>  │  11:40 – 12:20
<b>6 урок</b>  │  12:30 – 13:10
<code>──────────────────────────</code>
<i>Перемены: 10 мин | после 2-го урока: 15 мин</i>
"""


# ─────────────────────────────────────────────
#  Обработчики
# ─────────────────────────────────────────────

@router.message(F.text == "📚 Подготовка к ОГЭ")
async def oge_prep_handler(message: Message) -> None:
    """Показываем меню выбора предмета."""
    await message.answer(
        "📚 <b>Подготовка к ОГЭ 2026</b>\n\n"
        "Выбери предмет — получишь ссылки на лучшие справочники, "
        "тренажёры и видеоуроки:\n\n"
        "<i>💡 Совет: начинай с обязательных предметов — "
        "математики и русского языка.</i>",
        reply_markup=get_oge_subjects_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.in_(OGE_SUBJECTS.keys()))
async def oge_subject_handler(callback: CallbackQuery) -> None:
    """Показываем ресурсы по выбранному предмету."""
    subject_key = callback.data
    subject_name, _ = OGE_SUBJECTS[subject_key]

    await callback.message.edit_text(
        f"{subject_name} — <b>материалы для подготовки</b>\n\n"
        "Нажми на нужный ресурс, чтобы открыть его:",
        reply_markup=get_subject_resources_keyboard(subject_key),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "oge_back")
async def oge_back_handler(callback: CallbackQuery) -> None:
    """Возврат к выбору предмета."""
    await callback.message.edit_text(
        "📚 <b>Подготовка к ОГЭ 2026</b>\n\n"
        "Выбери предмет — получишь ссылки на лучшие справочники, "
        "тренажёры и видеоуроки:\n\n"
        "<i>💡 Совет: начинай с обязательных предметов — "
        "математики и русского языка.</i>",
        reply_markup=get_oge_subjects_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(F.text == "🔔 Расписание звонков")
async def bells_handler(message: Message) -> None:
    """Красивый вывод расписания звонков."""
    await message.answer(BELLS_SCHEDULE, parse_mode="HTML")
