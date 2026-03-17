import datetime
import random
import asyncio
import aiohttp
from typing import AsyncGenerator

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.chat_action import ChatActionSender

from config.settings import config

router = Router()


# ─────────────────────────────────────────────
#  ФИЧА 1: Живой таймер до ОГЭ 2026
# ─────────────────────────────────────────────

# Ключевые даты основного периода ОГЭ 2026
OGE_DATES: list[tuple[str, datetime.date]] = [
    ("📐 Математика (основная)",        datetime.date(2026, 6,  3)),
    ("✍️ Русский язык",                  datetime.date(2026, 5, 27)),
    ("🌍 Обществознание",               datetime.date(2026, 6,  9)),
    ("🇬🇧 Английский (устная часть)",   datetime.date(2026, 5, 20)),
    ("💻 Информатика",                   datetime.date(2026, 6, 15)),
    ("⚛️ Физика",                        datetime.date(2026, 6,  5)),
    ("🧬 Биология",                      datetime.date(2026, 6, 11)),
    ("📜 История",                       datetime.date(2026, 6,  7)),
]

def _progress_bar(percent: float, length: int = 12) -> str:
    """Генерирует ASCII прогресс-бар."""
    filled = int(length * percent / 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"

def _get_countdown_text() -> str:
    today = datetime.date.today()
    # Год начала учебного года (1 сентября предыдущего года)
    school_start = datetime.date(today.year if today.month >= 9 else today.year - 1, 9, 1)
    nearest_exam = min(OGE_DATES, key=lambda x: abs((x[1] - today).days))

    lines = [
        "⏳ <b>Обратный отсчёт до ОГЭ 2026</b>",
        f"<code>{'─' * 30}</code>",
    ]

    for subject, date in sorted(OGE_DATES, key=lambda x: x[1]):
        delta = (date - today).days
        if delta < 0:
            status = "✅ Сдан"
        elif delta == 0:
            status = "🔥 <b>Сегодня!</b>"
        elif delta <= 7:
            status = f"⚠️ Через <b>{delta} дн.</b>"
        else:
            status = f"📅 {delta} дн."
        lines.append(f"{subject}\n    {status} — {date.strftime('%d.%m')}")

    # Общий прогресс учебного года до первого экзамена
    first_exam = min(d for _, d in OGE_DATES)
    total_days = (first_exam - school_start).days
    passed_days = (today - school_start).days
    percent = max(0, min(100, passed_days / total_days * 100))

    lines += [
        f"<code>{'─' * 30}</code>",
        f"📊 Готовность к сезону: <b>{percent:.0f}%</b>",
        f"<code>{_progress_bar(percent, 20)}</code>",
        "",
        f"<i>Ближайший экзамен: {nearest_exam[0]}</i>",
    ]
    return "\n".join(lines)


@router.message(Command("oge_timer"))
async def oge_countdown(message: Message) -> None:
    await message.answer(_get_countdown_text(), parse_mode="HTML")


# ─────────────────────────────────────────────
#  ФИЧА 2: Нейро-помощник (DeepSeek API)
# ─────────────────────────────────────────────

class AskAIStates(StatesGroup):
    waiting_for_question = State()

# Системный промпт — настраивает модель под школьника 9-го класса
_SYSTEM_PROMPT = """Ты — умный учебный ассистент для школьников 9-го класса.
Твоя задача:
- Объяснять темы простым языком, давая примеры.
- Помогать готовиться к ОГЭ по математике, русскому, обществознанию, истории, биологии, физике и информатике.
- Если вопрос не связан с учёбой, вежливо сообщи об этом.
Отвечай на русском языке. Используй HTML-форматирование: <b>, <i>, <code>.
Структурируй ответ — используй разделы, примеры, краткие выводы."""

_AI_THINKING_PHRASES = [
    "🧠 Анализирую вопрос...",
    "📡 Обращаюсь к базе знаний...",
    "⚙️ Генерирую ответ...",
]


async def _call_deepseek(question: str) -> str:
    """
    Запрос к DeepSeek API (OpenAI-совместимый).
    Требует DEEPSEEK_API_KEY в .env / config.
    """
    api_key: str = getattr(config, "deepseek_api_key", "").strip()
    if not api_key:
        return (
            "⚠️ <b>AI-ассистент не настроен.</b>\n\n"
            "Администратор не добавил <code>DEEPSEEK_API_KEY</code> в конфиг.\n"
            "Пока можешь использовать /fact для получения полезных фактов."
        )

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system",  "content": _SYSTEM_PROMPT},
            {"role": "user",    "content": question},
        ],
        "max_tokens": 700,
        "temperature": 0.6,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                if resp.status != 200:
                    error_body = await resp.text()
                    return f"❌ Ошибка API ({resp.status}): {error_body[:200]}"
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    except asyncio.TimeoutError:
        return "⏱ Время ожидания ответа истекло. Попробуй ещё раз."
    except Exception as e:
        return f"❌ Непредвиденная ошибка: {e}"


@router.message(Command("ask_ai"))
async def ask_neural_network(message: Message, bot: Bot) -> None:
    """Задать вопрос AI-ассистенту через команду: /ask_ai <вопрос>"""
    question = message.text.replace("/ask_ai", "", 1).strip()

    if not question:
        await message.answer(
            "🤖 <b>Нейро-ассистент</b>\n\n"
            "Задай вопрос прямо в команде:\n"
            "<code>/ask_ai Объясни теорему Пифагора</code>\n\n"
            "Или просто напиши <code>/ask_ai</code> — и я переведу тебя в режим диалога.",
            parse_mode="HTML",
        )
        return

    thinking_msg = await message.answer(random.choice(_AI_THINKING_PHRASES))

    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        answer = await _call_deepseek(question)

    await thinking_msg.delete()
    await message.answer(
        f"🤖 <b>Ответ ассистента:</b>\n\n{answer}",
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────
#  ФИЧА 3: Рандомный факт по предметам
# ─────────────────────────────────────────────

_FACTS: dict[str, list[str]] = {
    "📐 Математика": [
        "Квадрат гипотенузы равен сумме квадратов катетов (теорема Пифагора). Запомни: 3²+4²=5².",
        "Дискриминант D = b²−4ac. Если D > 0 — два корня, D = 0 — один, D < 0 — нет вещественных корней.",
        "Медиана треугольника делит его площадь пополам и делится точкой пересечения в отношении 2:1 от вершины.",
    ],
    "✍️ Русский язык": [
        "Краткие прилагательные в предложении всегда являются именной частью составного сказуемого, а не определением.",
        "«Н» и «НН»: в кратких причастиях всегда пишется одна «Н», даже если в полном было «НН».",
        "Запятая перед «как» ставится, если оборот имеет значение причины или присоединяет придаточное.",
    ],
    "🌍 Обществознание": [
        "Социальная мобильность бывает вертикальной (изменение статуса) и горизонтальной (без изменения статуса).",
        "Формы государственного правления: монархия (абсолютная / конституционная) и республика (президентская / парламентская).",
        "Потребности по Маслоу снизу вверх: физиологические → безопасность → социальные → престиж → самореализация.",
    ],
    "📜 История": [
        "Крепостное право в России отменено Александром II 19 февраля (3 марта) 1861 года — Манифестом об освобождении крестьян.",
        "Опричнина Ивана Грозного действовала с 1565 по 1572 год — период государственного террора против бояр.",
        "Куликовская битва — 8 сентября 1380 года. Дмитрий Донской разгромил ордынское войско Мамая на Куликовом поле.",
    ],
    "⚛️ Физика": [
        "Закон Ома: I = U/R. Сила тока прямо пропорциональна напряжению и обратно пропорциональна сопротивлению.",
        "При последовательном соединении сопротивления складываются: R = R₁ + R₂. При параллельном: 1/R = 1/R₁ + 1/R₂.",
        "Угол падения луча всегда равен углу отражения — закон отражения света.",
    ],
    "🧬 Биология": [
        "ДНК расшифровывается как дезоксирибонуклеиновая кислота. Она хранит наследственную информацию в ядре клетки.",
        "Фотосинтез: 6CO₂ + 6H₂O → C₆H₁₂O₆ + 6O₂. Свет — необходимое условие. Хлорофилл поглощает красный и синий свет.",
        "Митоз — деление соматических клеток, в результате которого образуются 2 клетки с одинаковым набором хромосом.",
    ],
    "🇬🇧 Английский": [
        "Present Perfect vs Past Simple: если есть конкретное время (yesterday, in 2020) → Past Simple; если нет → Present Perfect.",
        "Конструкция used to + V₁ обозначает прошлую привычку: «I used to play football» — «Я раньше играл в футбол».",
        "Модальные глаголы (can, must, should) не имеют окончания -s в 3-м лице и не используют вспомогательный do/does.",
    ],
}


def _random_fact() -> str:
    subject = random.choice(list(_FACTS.keys()))
    fact    = random.choice(_FACTS[subject])
    return f"💡 <b>Факт для ОГЭ — {subject}</b>\n\n{fact}"


@router.message(Command("fact"))
async def random_smart_fact(message: Message) -> None:
    """Случайный полезный факт для подготовки к ОГЭ."""
    await message.answer(_random_fact(), parse_mode="HTML")


# ─────────────────────────────────────────────
#  ФИЧА 4: Команда /study — открыть Mini App
# ─────────────────────────────────────────────

@router.message(Command("study"))
async def open_mini_app(message: Message) -> None:
    """Показываем кнопку для запуска Mini App."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    webapp_url: str = getattr(config, "webapp_url", "").strip()

    if not webapp_url:
        await message.answer(
            "⚙️ <b>Mini App не настроен.</b>\n\n"
            "Добавьте <code>WEBAPP_URL</code> в файл <code>.env</code>, "
            "указав публичный URL вашего <code>webapp/index.html</code>.",
            parse_mode="HTML",
        )
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🖥 Открыть Учебный Терминал",
            web_app={"url": webapp_url},
        )
    ]])
    await message.answer(
        "🖥 <b>Учебный Терминал</b>\n\n"
        "Нажми кнопку ниже, чтобы открыть интерактивный интерфейс прямо в Telegram:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
