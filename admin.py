from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from config.settings import config
from database.models import async_session, User

router = Router()


# ─────────────────────────────────────────────
#  FSM — состояния для рассылки
# ─────────────────────────────────────────────

class BroadcastStates(StatesGroup):
    choosing_type = State()   # выбор типа уведомления
    typing_message = State()  # ввод текста
    confirming = State()      # подтверждение перед отправкой


# ─────────────────────────────────────────────
#  Фильтр: только администратор
# ─────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


# ─────────────────────────────────────────────
#  Клавиатуры
# ─────────────────────────────────────────────

def get_broadcast_type_keyboard() -> InlineKeyboardMarkup:
    """Выбор типа рассылки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Изменение расписания", callback_data="broadcast_schedule"),
            InlineKeyboardButton(text="📢 Общее объявление",     callback_data="broadcast_general"),
        ],
        [
            InlineKeyboardButton(text="⚠️ Срочное уведомление",  callback_data="broadcast_urgent"),
            InlineKeyboardButton(text="📝 Домашнее задание",      callback_data="broadcast_homework"),
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel"),
        ],
    ])


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение рассылки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить всем", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="✏️ Изменить текст",  callback_data="broadcast_rewrite"),
        ],
        [
            InlineKeyboardButton(text="❌ Отменить",        callback_data="broadcast_cancel"),
        ],
    ])


# ─────────────────────────────────────────────
#  Вспомогательные функции
# ─────────────────────────────────────────────

# Иконки и префиксы для каждого типа рассылки
BROADCAST_LABELS: dict[str, tuple[str, str]] = {
    "broadcast_schedule": ("📅", "ИЗМЕНЕНИЕ РАСПИСАНИЯ"),
    "broadcast_general":  ("📢", "ОБЪЯВЛЕНИЕ"),
    "broadcast_urgent":   ("⚠️", "СРОЧНО"),
    "broadcast_homework": ("📝", "ДОМАШНЕЕ ЗАДАНИЕ"),
}


def format_broadcast(cb_type: str, text: str) -> str:
    icon, title = BROADCAST_LABELS.get(cb_type, ("📌", "УВЕДОМЛЕНИЕ"))
    return (
        f"{icon} <b>{title}</b>\n"
        f"{'─' * 28}\n"
        f"{text}\n\n"
        f"<i>— Уведомление от администратора</i>"
    )


async def get_all_user_ids() -> list[int]:
    """Получить tg_id всех пользователей из БД."""
    async with async_session() as session:
        result = await session.execute(select(User.tg_id))
        return [row[0] for row in result.fetchall()]


async def do_broadcast(bot: Bot, text: str) -> tuple[int, int]:
    """
    Разослать сообщение всем пользователям.
    Возвращает (успешно, ошибок).
    """
    user_ids = await get_all_user_ids()
    success, failed = 0, 0

    for uid in user_ids:
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1

    return success, failed


# ─────────────────────────────────────────────
#  Команды и обработчики
# ─────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    """Главная панель администратора."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    text = (
        "🛠 <b>Панель администратора</b>\n\n"
        "Доступные команды:\n"
        "• /broadcast — рассылка уведомлений\n"
        "• /stats — статистика пользователей\n"
        "• /userlist — список всех учеников\n"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("broadcast"))
async def start_broadcast(message: Message, state: FSMContext) -> None:
    """Запуск процесса рассылки."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    await state.set_state(BroadcastStates.choosing_type)
    await message.answer(
        "📣 <b>Создание рассылки</b>\n\n"
        "Выберите тип уведомления, которое вы хотите отправить ученикам:",
        reply_markup=get_broadcast_type_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(BroadcastStates.choosing_type, F.data.startswith("broadcast_"))
async def choose_broadcast_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора типа рассылки."""
    if callback.data == "broadcast_cancel":
        await state.clear()
        await callback.message.edit_text("❌ Рассылка отменена.")
        return

    await state.update_data(broadcast_type=callback.data)
    await state.set_state(BroadcastStates.typing_message)

    _, label = BROADCAST_LABELS.get(callback.data, ("📌", "УВЕДОМЛЕНИЕ"))
    await callback.message.edit_text(
        f"✏️ <b>Тип: {label}</b>\n\n"
        "Введите текст сообщения, которое получат все ученики.\n"
        "<i>Поддерживается HTML-форматирование: &lt;b&gt;, &lt;i&gt;, &lt;code&gt;</i>",
        parse_mode="HTML",
    )


@router.message(BroadcastStates.typing_message)
async def receive_broadcast_text(message: Message, state: FSMContext) -> None:
    """Получение текста от администратора и показ превью."""
    data = await state.get_data()
    broadcast_type: str = data.get("broadcast_type", "broadcast_general")
    raw_text = message.text or ""

    formatted = format_broadcast(broadcast_type, raw_text)
    await state.update_data(formatted_text=formatted)
    await state.set_state(BroadcastStates.confirming)

    await message.answer(
        f"👁 <b>Предпросмотр сообщения:</b>\n\n{formatted}\n\n"
        "Подтвердите отправку или внесите изменения:",
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(BroadcastStates.confirming, F.data == "broadcast_confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Подтверждение и отправка рассылки."""
    data = await state.get_data()
    text: str = data.get("formatted_text", "")

    await callback.message.edit_text("⏳ Выполняю рассылку...")
    success, failed = await do_broadcast(bot, text)

    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"• Доставлено: <b>{success}</b> получателей\n"
        f"• Ошибок: <b>{failed}</b>\n\n"
        f"<i>Недоставленные — боты или заблокировавшие бота пользователи.</i>",
        parse_mode="HTML",
    )


@router.callback_query(BroadcastStates.confirming, F.data == "broadcast_rewrite")
async def rewrite_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуться к вводу текста."""
    await state.set_state(BroadcastStates.typing_message)
    await callback.message.edit_text(
        "✏️ Введите новый текст сообщения:",
        parse_mode="HTML",
    )


@router.callback_query(BroadcastStates.confirming, F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена на этапе подтверждения."""
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена.")


# ─────────────────────────────────────────────
#  Дополнительные команды статистики
# ─────────────────────────────────────────────

@router.message(Command("stats"))
async def stats_handler(message: Message) -> None:
    """Статистика зарегистрированных пользователей."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    async with async_session() as session:
        total_result   = await session.execute(select(User))
        admin_result   = await session.execute(select(User).where(User.is_admin == True))  # noqa: E712
        total   = len(total_result.scalars().all())
        admins  = len(admin_result.scalars().all())

    await message.answer(
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{total}</b>\n"
        f"🛠 Администраторов: <b>{admins}</b>\n"
        f"🎓 Учеников: <b>{total - admins}</b>",
        parse_mode="HTML",
    )


@router.message(Command("userlist"))
async def userlist_handler(message: Message) -> None:
    """Список всех учеников."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    async with async_session() as session:
        result = await session.execute(select(User).order_by(User.id))
        users: list[User] = result.scalars().all()

    if not users:
        await message.answer("📭 Пользователей пока нет.")
        return

    lines = ["👥 <b>Список пользователей:</b>\n"]
    for u in users:
        role = "🛠 Админ" if u.is_admin else "🎓 Ученик"
        name = f"@{u.username}" if u.username else f"id:{u.tg_id}"
        lines.append(f"• {name} — {role} (класс {u.grade_level})")

    await message.answer("\n".join(lines), parse_mode="HTML")
