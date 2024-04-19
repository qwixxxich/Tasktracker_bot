from aiogram.filters import Command
from aiogram import Router, types
from bot.config import BotConfig
from bot.bot_instance import bot
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import StateFilter
from datetime import datetime

from aiogram import F
from keyboards import *
from functions import *

user_router = Router()


class UserState(StatesGroup):
    user_FullName = State()
    task_name = State()
    task_description = State()
    task_date = State()
    task_user_choice = State()


# Initial messages


@user_router.message(Command("start"))
async def start(message: types.Message, config: BotConfig, state: FSMContext):
    if message.text in ["/start", "/cancel"]:
        user_id = message.from_user.id
        has_access = await get_accessed_ids(config.db_connection, user_id)
        if has_access:
            await message.answer(
                "Привет! Я твой помощник по управлению задачами",
                reply_markup=await start_kb(user_id, config),
            )
        else:
            await message.answer(
                "Для получения доступа к боту перейдите по специальной ссылке"
            )
    else:
        split = message.text.split(" ")[1]
        if split.startswith("del_user"):
            _, _, user_id, message_id = split.split("_")

            if await check_user_tasks(config.db_connection, user_id):
                await message.answer(
                    "У пользователя есть невыполненные задачи. Прежде чем удалить участника, сними с него задачи."
                )
            else:
                await bot.delete_message(message.chat.id, message_id)
                async with config.db_connection.execute(
                    "SELECT FullName FROM user WHERE user_id = ?", (user_id,)
                ) as cursor:
                    FullName = await cursor.fetchone()
                await config.db_connection.execute(
                    "DELETE FROM user WHERE user_id = ?", (user_id,)
                )
                await config.db_connection.commit()
                await message.answer(f"Участник {FullName[0]} удален(а)")
                await safe_start(message, config, state, user_id)
        elif split == "4af1e479":
            user_id = message.from_user.id
            has_access = await get_accessed_ids(config.db_connection, user_id)
            if has_access:
                await message.answer("У тебя уже есть доступ к боту.")
            else:
                await message.answer(
                    'Пожалуйста, напиши своё <i>имя</i> и <i>фамилию</i> через пробел (Пример: "Иван Иванов")',
                    parse_mode="HTML",
                )
                await state.set_state(UserState.user_FullName)
        elif split.startswith("check_task"):
            _, _, task_id = split.split("_")
            async with config.db_connection.execute(
                "SELECT TaskName, TaskDescription, TaskDate, TaskParticipants FROM tasks WHERE id = ?",
                (task_id,),
            ) as cursor:
                task = await cursor.fetchone()
            task_participants = task[3].split(",")
            list_of_names = ""
            for user_id in task_participants:
                async with config.db_connection.execute(
                    "SELECT FullName FROM user WHERE user_id = ?", (user_id,)
                ) as cursor:
                    user = await cursor.fetchone()
                list_of_names += f"\n{user[0]}"
            task_text = f"Название: {task[0]}\nОписание: {task[1]}\nДедлайн: {task[2]}\n\nУчастники:{list_of_names}"
            await message.answer(task_text, reply_markup=await back_to_menu_kb())
        elif split.startswith("check_user"):
            _, _, user_id, message_id = split.split("_")
            async with config.db_connection.execute(
                "SELECT id, TaskName, TaskDate FROM tasks WHERE TaskParticipants LIKE '%' || ? || '%' AND status = 0",
                (user_id,),
            ) as cursor:
                tasks = await cursor.fetchall()
                if len(tasks) > 60:
                    tasks = tasks[:60]
            if len(tasks) > 0:
                task_list = "\n".join(
                    [
                        f'{task[1]} ({task[2]}) - <a href="https://t.me/Taskcracker_bot?start=check_task_{task[0]}">Посмотреть задачу</a>'
                        for task in tasks
                    ]
                )
                await message.answer(
                    f"У пользователя есть невыполненные задачи:\n\n{task_list}",
                    parse_mode="HTML",
                    reply_markup=await back_to_team_kb(),
                )
            else:
                await message.answer("У пользователя нет невыполненных задач.")


async def safe_start(
    message: types.Message, config: BotConfig, state: FSMContext, user_id: int = None
):
    await state.clear()
    has_access = await get_accessed_ids(config.db_connection, user_id)
    if has_access:
        await message.answer(
            "Привет! Я твой помощник по управлению задачами",
            reply_markup=await start_kb(user_id, config),
        )
    else:
        await message.answer(
            "Для получения доступа к боту перейдите по специальной ссылке"
        )


async def start_edit(message: types.Message, user_id: int, config: BotConfig):
    await message.edit_text(
        "Привет! Я твой помощник по управлению задачами",
        reply_markup=await start_kb(user_id, config),
    )


@user_router.message(Command("cancel"))
async def cancel(message: types.Message, config: BotConfig, state: FSMContext):
    await state.clear()
    await start(message, config, state)


@user_router.message(StateFilter(UserState.user_FullName))
async def get_user_fullname(
    message: types.Message, config: BotConfig, state: FSMContext
):
    await state.clear()
    user_fullname = message.text
    user_id = message.from_user.id
    user_name = message.from_user.username
    if user_name is None:
        user_name = "UserWithoutUsername"

    async with config.db_connection.execute(
        "SELECT * FROM user WHERE user_id = ?", (user_id,)
    ) as cursor:
        user_exists = await cursor.fetchone()
    if user_exists:
        await config.db_connection.execute(
            "UPDATE user SET FullName = ?, UserName = ? WHERE user_id = ?",
            (user_fullname, user_name, user_id),
        )
        await message.answer("Данные обновлены.")
    else:
        await config.db_connection.execute(
            "INSERT INTO user (user_id, FullName, UserName) VALUES (?, ?, ?)",
            (user_id, user_fullname, user_name),
        )
        await message.answer(
            "Доступ предоставлен. Теперь ты можешь пользоваться ботом."
        )
    await config.db_connection.commit()
    await safe_start(message, config, state, user_id)


@user_router.callback_query(F.data == "cancel_edit")
async def cancel_creation(
    callback: types.CallbackQuery, state: FSMContext, config: BotConfig
):
    await state.clear()
    user_id = callback.from_user.id
    await start_edit(callback.message, user_id, config)


@user_router.callback_query(F.data == "safe_start")
async def safe_start_callback(
    callback: types.CallbackQuery, config: BotConfig, state: FSMContext
):
    user_id = callback.from_user.id
    await callback.message.delete_reply_markup()
    await safe_start(callback.message, config, state, user_id)


# Task creation


@user_router.callback_query(F.data == "create_task")
async def create_task(callback: types.CallbackQuery, state: FSMContext):
    message = await callback.message.edit_text(
        "Введи короткое название задачи (До 30 символов)",
        reply_markup=await cancel_edit(),
    )
    await state.set_state(UserState.task_name)
    await state.update_data(message_id=message.message_id)


@user_router.message(UserState.task_name)
async def get_task_name(message: types.Message, state: FSMContext):
    task_name = message.text
    if len(task_name) > 30:
        await message.answer("Слишком длинное название. Попробуй еще раз.")
    else:
        data = await state.get_data()
        message_id = data["message_id"]
        await state.clear()
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id, message_id=message_id, reply_markup=None
        )
        message = await message.answer(
            "Теперь введи описание задачи (До 4096 символов)",
            reply_markup=await cancel_edit(),
        )
        await state.set_state(UserState.task_description)
        await state.update_data(task_name=task_name, message_id=message.message_id)


@user_router.message(UserState.task_description)
async def get_task_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task_name = data["task_name"]
    message_id = data["message_id"]
    task_description = message.text
    await state.clear()
    await bot.edit_message_reply_markup(
        chat_id=message.chat.id, message_id=message_id, reply_markup=None
    )
    date = datetime.now()
    markup = await month_calendar_kb(date.year, date.month)
    await message.answer("Теперь выбери дедлайн задачи:", reply_markup=markup)
    await state.set_state(UserState.task_date)
    await state.update_data(task_name=task_name, task_description=task_description)


@user_router.callback_query(UserState.task_date, F.data.startswith("select-day:"))
async def get_task_date(
    callback: types.CallbackQuery, state: FSMContext, config: BotConfig
):
    _, year, month, day = callback.data.split(":")
    if len(day) == 1:
        day = f"0{day}"
    if len(month) == 1:
        month = f"0{month}"
    chosen_date = f"{year}.{month}.{day}"
    await callback.message.delete()
    await callback.message.answer(f"Выбран дедлайн: {chosen_date}", show_alert=True)
    data = await state.get_data()
    task_name = data["task_name"]
    task_description = data["task_description"]
    await state.clear()

    users = await config.db_connection.execute_fetchall(
        "SELECT user_id, FullName FROM user"
    )
    await callback.message.answer(
        "Ответственные лица:", reply_markup=await team_choice_kb(users)
    )
    await state.set_state(UserState.task_user_choice)
    await state.update_data(
        task_name=task_name, task_description=task_description, chosen_date=chosen_date
    )


@user_router.callback_query(
    F.data.startswith("select_user:"), UserState.task_user_choice
)
async def select_user(
    callback: types.CallbackQuery, state: FSMContext, config: BotConfig
):
    user_id = int(callback.data.split(":")[1])

    data = await state.get_data()
    selected_users = data.get("selected_users", [])

    if user_id in selected_users:
        selected_users.remove(user_id)
    else:
        selected_users.append(user_id)

    await state.update_data(selected_users=selected_users)

    users = await config.db_connection.execute_fetchall(
        "SELECT user_id, FullName FROM user"
    )
    await callback.message.edit_reply_markup(
        reply_markup=await team_choice_kb(users, selected_users)
    )

    await callback.answer()


@user_router.callback_query(F.data == "submit", UserState.task_user_choice)
async def submit_selection(
    callback: types.CallbackQuery, state: FSMContext, config: BotConfig
):
    state_data = await state.get_data()
    selected_users = state_data["selected_users"]

    if selected_users:
        await callback.message.delete()
        task_name = state_data["task_name"]
        task_description = state_data["task_description"]
        chosen_date = state_data["chosen_date"]
        await state.clear()

        placeholders = ",".join("?" for user_id in selected_users)
        users_query = f"SELECT user_id, FullName, Username FROM user WHERE user_id IN ({placeholders})"
        users = await config.db_connection.execute_fetchall(users_query, selected_users)

        selected_users_text = "\n".join([f"{user[1]} - @{user[2]}" for user in users])

        await callback.message.answer(f"Участники:\n{selected_users_text}")
        selected_users_string = ",".join([str(user[0]) for user in users])

        async with config.db_connection.execute(
            "SELECT IFNULL(MAX(id), 0) FROM tasks"
        ) as cursor:
            result = await cursor.fetchone()
        uniq_id = result[0] + 1
        await config.db_connection.execute(
            "INSERT INTO tasks (TaskName, TaskDescription, TaskDate, TaskParticipants, id) VALUES (?, ?, ?, ?, ?, ?)",
            (
                task_name,
                task_description,
                chosen_date,
                selected_users_string,
                uniq_id,
                0,
            ),
        )
        await config.db_connection.commit()

        for user in users:
            await bot.send_message(
                user[0],
                f"❗️ Внимание. Новая задача: {task_name}\nПодробности: [Здесь](https://t.me/Taskcracker_bot?start=check_task_{uniq_id})",
                parse_mode="Markdown",
            )
        await callback.message.answer(
            "Задача создана! Всем участникам отправлено уведомление."
        )
        await safe_start(callback.message, config, state, callback.from_user.id)
    else:
        await callback.message.answer("Выбери хотя бы одного участника")


@user_router.callback_query(F.data.startswith("next-month:"))
async def handle_next_month(callback: types.CallbackQuery):
    _, year, month = callback.data.split(":")
    year, month = int(year), int(month)
    month += 1
    if month > 12:
        month = 1
        year += 1
    markup = await month_calendar_kb(year, month)
    await callback.message.edit_text("Выберите дату:", reply_markup=markup)
    await callback.answer()


@user_router.callback_query(F.data.startswith("prev-month:"))
async def handle_prev_month(callback: types.CallbackQuery):
    _, year, month = callback.data.split(":")
    year, month = int(year), int(month)
    month -= 1
    if month < 1:
        month = 12
        year -= 1
    markup = await month_calendar_kb(year, month)
    await callback.message.edit_text("Выберите дату:", reply_markup=markup)
    await callback.answer()


@user_router.callback_query(F.data.startswith("choose-month:"))
async def handle_month_chosen(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if (callback.data).count(":") == 2:
        _, month, check = callback.data.split(":")
    else:
        _, month = callback.data.split(":")
        check = "no_check"
    month = int(month)

    year = user_choices.get(user_id, {}).get("year", datetime.now().year)
    user_choices[user_id] = {"year": year, "month": month}

    if check == "check":
        markup = await month_calendar_kb(year, month)
        await callback.message.edit_text("Выберите дату:", reply_markup=markup)
    else:
        markup = await generate_month_selection_keyboard(year, month)
        await callback.message.edit_text("Выберите месяц:", reply_markup=markup)


@user_router.callback_query(F.data.startswith("prev-year:"))
async def handle_prev_year(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, year = callback.data.split(":")
    year = int(year) - 1

    now = datetime.now()
    month = now.month if year == now.year else 1

    user_choices[user_id] = {"year": year, "month": month}

    markup = await month_calendar_kb(year, month)
    await callback.message.edit_text("Выберите дату:", reply_markup=markup)


@user_router.callback_query(F.data.startswith("next-year:"))
async def handle_next_year(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, year = callback.data.split(":")
    year = int(year) + 1

    month = 1

    user_choices[user_id] = {"year": year, "month": month}

    markup = await month_calendar_kb(year, month)
    await callback.message.edit_text("Выберите дату:", reply_markup=markup)


# Task viewing


@user_router.callback_query(F.data.startswith("show_tasks_foradmin"))
async def show_tasks(callback: types.CallbackQuery, config: BotConfig):
    page = int(callback.data.split("|")[1])
    await callback.message.edit_text(
        "Задачи по дедлайнам, начиная с самых ближайших:",
        reply_markup=await get_tasks_page_foradmin(config.db_connection, page),
    )


@user_router.callback_query(F.data.startswith("show_tasks_foruser"))
async def show_tasks(callback: types.CallbackQuery, config: BotConfig):
    page = int(callback.data.split("|")[1])
    await callback.message.edit_text(
        "Твои задачи:",
        reply_markup=await get_tasks_page(
            config.db_connection, callback.from_user.id, page
        ),
    )


# Team


@user_router.callback_query(F.data == "team")
async def team(callback: types.CallbackQuery, config: BotConfig):
    placeholders = ",".join("?" * len(config.user_id_list))

    query = f"""
    SELECT user_id, FullName, UserName, 
           CASE WHEN user_id IN ({placeholders}) THEN 'admin' ELSE 'user' END as Role
    FROM user
    """

    async with config.db_connection.execute(query, config.user_id_list) as cursor:
        all_users = await cursor.fetchall()

    admin_list, team_list = [], []
    for user in all_users:
        user_info = f"{user[1]} - @{user[2]}"
        if user[3] == "admin":
            admin_list.append(
                user_info
                + f' <a href="https://t.me/Taskcracker_bot?start=check_user_{user[0]}_{callback.message.message_id}">Посмотреть задачи</a>'
            )
        else:
            team_list.append(
                user_info
                + f' <a href="https://t.me/Taskcracker_bot?start=check_user_{user[0]}_{callback.message.message_id}">Посмотреть задачи</a> <a href="https://t.me/Taskcracker_bot?start=del_user_{user[0]}_{callback.message.message_id}">Удалить</a>'
            )

    admin_text = (
        "Админы:\n\n" + "\n".join(admin_list) + "\n\n"
        if admin_list
        else "Админы:\n\nНет администраторов.\n\n"
    )
    team_text = (
        "Команда:\n\n" + "\n".join(team_list)
        if team_list
        else "Команда:\n\nУчастники не найдены.\n\n"
    )

    final_text = admin_text + team_text

    await callback.message.edit_text(
        final_text,
        reply_markup=await cancel_edit(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# Settings


@user_router.callback_query(F.data == "settings")
async def settings(callback: types.CallbackQuery):
    await callback.message.edit_text("Настройки:", reply_markup=await settings_kb())


@user_router.callback_query(F.data == "change_name")
async def change_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        'Введи новое <i>имя</i> и <i>фамилию</i> через пробел (Пример: "Иван Иванов")',
        parse_mode="HTML",
    )
    await state.set_state(UserState.user_FullName)
