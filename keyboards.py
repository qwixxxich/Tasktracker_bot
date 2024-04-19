from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
import calendar
from datetime import datetime
from bot.config import BotConfig

MONTH_NAMES = [
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]
user_choices = {}


async def start_kb(user_id, config: BotConfig):
    kb = InlineKeyboardBuilder()
    if user_id in config.user_id_list:
        kb.button(text="Создать задачу", callback_data="create_task")
        kb.button(text="Посмотреть все задачи", callback_data="show_tasks_foradmin|1")
        kb.button(text="Команда", callback_data="team")
        kb.button(text="Настройки", callback_data="settings")
    else:
        kb.button(text="Мои задачи", callback_data="show_tasks_foruser|1")
        kb.button(text="Настройки", callback_data="settings")
    kb.adjust(1)

    return kb.as_markup()


async def cancel_edit():
    kb = InlineKeyboardBuilder()
    kb.button(text="Отмена", callback_data="cancel_edit")
    return kb.as_markup()


async def settings_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Изменить имя и фамилию", callback_data="change_name")
    kb.button(text="Отмена", callback_data="cancel_edit")
    kb.adjust(1)
    return kb.as_markup()


async def team_choice_kb(users):
    kb = InlineKeyboardBuilder()
    for user in users:
        full_name = user[1]
        user_id = user[0]
        callback_data = f"select_user:{user_id}"
        kb.button(text=full_name, callback_data=callback_data)
    kb.button(text="Отмена", callback_data="cancel_edit")
    kb.adjust(1)
    return kb.as_markup()


async def team_choice_kb(users, selected_users=None):
    if selected_users is None:
        selected_users = []
    kb = InlineKeyboardBuilder()
    for user_id, full_name in users:
        prefix = "✅" if user_id in selected_users else ""
        text = f"{prefix} {full_name}"
        callback_data = f"select_user:{user_id}"
        kb.button(text=text, callback_data=callback_data)
    kb.button(text="🆗 Подтвердить", callback_data="submit")
    kb.button(text="Отмена", callback_data="cancel_edit")
    kb.adjust(1)
    return kb.as_markup()


async def month_calendar_kb(year: int, month: int):
    now = datetime.now()
    is_current_year = year == now.year
    is_current_month = is_current_year and month == now.month

    kb = InlineKeyboardBuilder()

    kb.button(text=MONTH_NAMES[month - 1], callback_data=f"choose-month:{month}")
    if is_current_year:
        kb.button(text="|", callback_data="ignore")
    else:
        kb.button(text="<", callback_data=f"prev-year:{year}")
    kb.button(text=str(year), callback_data=f"choose-year:{year}")
    kb.button(text=">", callback_data=f"next-year:{year}")

    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for day in days_of_week:
        kb.button(text=day, callback_data="ignore")

    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        for day in week:
            if day == 0 or (is_current_month and day < now.day):
                kb.button(text=" ", callback_data="ignore")
            else:
                kb.button(
                    text=str(day), callback_data=f"select-day:{year}:{month}:{day}"
                )

    if is_current_month:
        kb.button(text=">", callback_data=f"next-month:{year}:{month}")
    else:
        kb.button(text="<", callback_data=f"prev-month:{year}:{month}")
        kb.button(text=">", callback_data=f"next-month:{year}:{month}")

    total_weeks = len(month_calendar)
    kb.adjust(4, 7, *[7 for _ in range(total_weeks)], 2 if not is_current_month else 1)

    return kb.as_markup()


async def generate_month_selection_keyboard(year: int, month: int):
    now = datetime.now()
    kb = InlineKeyboardBuilder()

    start_month = now.month if year == now.year else 1

    for month in range(start_month, 13):
        kb.button(
            text=MONTH_NAMES[month - 1], callback_data=f"choose-month:{month}:check"
        )

    kb.adjust(1)
    return kb.as_markup()


async def get_tasks_page_foradmin(db_connection, page=1):
    tasks_per_page = 98
    offset = (page - 1) * tasks_per_page

    cursor = await db_connection.execute("SELECT COUNT(*) FROM tasks")
    total_tasks_row = await cursor.fetchone()
    total_tasks = total_tasks_row[0] if total_tasks_row else 0

    # Получаем задачи для текущей страницы
    cursor = await db_connection.execute(
        "SELECT id, TaskName, TaskDate FROM tasks ORDER BY TaskDate LIMIT ? OFFSET ?",
        (tasks_per_page, offset),
    )
    tasks = await cursor.fetchall()
    tasks_sorted = sorted(tasks, key=lambda x: datetime.strptime(x[2], "%Y.%m.%d"))

    kb = InlineKeyboardBuilder()

    for task in tasks_sorted:
        task_id, task_name, task_date = task
        task_date = datetime.strptime(task_date, "%Y.%m.%d").strftime("%d.%m.%Y")
        kb.button(
            text=f"{task_name}, до {task_date}",
            callback_data=f"task_view_for_admin|{task_id}",
        )

    kb.adjust(1)
    kb2 = InlineKeyboardBuilder()
    row = []
    if page == 1:
        row.append(InlineKeyboardButton(text="Отмена", callback_data="cancel_edit"))
    if page > 1:
        row.append(
            InlineKeyboardButton(
                text="<", callback_data=f"show_tasks_foradmin|{page - 1}"
            )
        )
    if total_tasks > page * tasks_per_page:
        row.append(
            InlineKeyboardButton(
                text=">", callback_data=f"show_tasks_foradmin|{page + 1}"
            )
        )
    kb2.add(*row)
    kb.attach(kb2)

    # Добавляем кнопку "Отмена" в любом случае

    return kb.as_markup()


async def get_tasks_page(db_connection, user_id, page=1):
    tasks_per_page = 98
    offset = (page - 1) * tasks_per_page

    cursor = await db_connection.execute(
        "SELECT COUNT(*) FROM tasks WHERE TaskParticipants LIKE '%' || ? || '%'",
        (user_id,),
    )
    total_tasks_row = await cursor.fetchone()
    total_tasks = total_tasks_row[0] if total_tasks_row else 0

    # Получаем задачи для текущей страницы
    cursor = await db_connection.execute(
        "SELECT id, TaskName, TaskDate FROM tasks WHERE TaskParticipants LIKE '%' || ? || '%' ORDER BY TaskDate LIMIT ? OFFSET ?",
        (user_id, tasks_per_page, offset),
    )
    tasks = await cursor.fetchall()
    tasks_sorted = sorted(tasks, key=lambda x: datetime.strptime(x[2], "%Y.%m.%d"))

    kb = InlineKeyboardBuilder()

    for task in tasks_sorted:
        task_id, task_name, task_date = task
        task_date = datetime.strptime(task_date, "%Y.%m.%d").strftime("%d.%m.%Y")
        kb.button(
            text=f"{task_name}, до {task_date}",
            callback_data=f"task_view_for_user|{task_id}",
        )

    kb.adjust(1)
    kb2 = InlineKeyboardBuilder()
    row = []
    if page == 1:
        row.append(InlineKeyboardButton(text="Отмена", callback_data="cancel_edit"))
    if page > 1:
        row.append(
            InlineKeyboardButton(
                text="<", callback_data=f"show_tasks_foruser|{page - 1}"
            )
        )
    if total_tasks > page * tasks_per_page:
        row.append(
            InlineKeyboardButton(
                text=">", callback_data=f"show_tasks_foruser|{page + 1}"
            )
        )
    kb2.add(*row)
    kb.attach(kb2)

    # Добавляем кнопку "Отмена" в любом случае

    return kb.as_markup()


async def back_to_team_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Назад", callback_data="team")
    return kb.as_markup()


async def back_to_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="В меню", callback_data="safe_start")
    return kb.as_markup()
