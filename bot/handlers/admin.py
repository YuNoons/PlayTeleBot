import json
import random
from aiogram import Router, Bot, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db import get_db, get_admin_level, log_admin_action, get_game, delete_game, save_game

admin_router = Router()

# State for selected rooms: admin_id -> chat_id
admin_selected_rooms = {}

class AdminStates(StatesGroup):
    waiting_for_select_room = State()
    waiting_for_skip_user = State()
    waiting_for_remove_user = State()
    waiting_for_add_coins = State()
    waiting_for_remove_coins = State()
    waiting_for_set_coins = State()
    waiting_for_give_title = State()
    waiting_for_reset_stats = State()
    waiting_for_shout = State()
    waiting_for_lottery = State()
    waiting_for_add_admin = State()
    waiting_for_remove_admin = State()

async def is_admin(user_id: int) -> bool:
    return await get_admin_level(user_id) > 0

async def is_main_admin(user_id: int) -> bool:
    return await get_admin_level(user_id) >= 2

def get_main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Комнаты", callback_data="admin_menu_rooms"), InlineKeyboardButton(text="🎮 Игра", callback_data="admin_menu_game")],
        [InlineKeyboardButton(text="💰 Экономика", callback_data="admin_menu_eco"), InlineKeyboardButton(text="🎉 Сюрпризы", callback_data="admin_menu_surprises")],
        [InlineKeyboardButton(text="👥 Админы", callback_data="admin_menu_admins")]
    ])

def get_cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]
    ])

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.chat.type != "private": return await message.answer("⚠️ Используйте эту команду в личке с ботом.")
    if not await is_admin(message.from_user.id): return await message.answer("⛔ Доступ запрещен.")
    await state.clear()
    await message.answer("🛠 <b>Админ-панель</b>\nВыберите раздел:", reply_markup=get_main_menu_kb(), parse_mode="HTML")

# Отмена любого действия
@admin_router.callback_query(F.data == "admin_cancel")
async def process_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено. Выберите раздел:", reply_markup=get_main_menu_kb())

# --- Навигация по меню ---
@admin_router.callback_query(F.data.startswith("admin_menu_"))
async def process_menus(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id): return await callback.answer("⛔ Доступ запрещен.", show_alert=True)
    menu = callback.data.replace("admin_menu_", "")
    
    if menu == "rooms":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👀 Показать активные комнаты", callback_data="admin_action_show_rooms")],
            [InlineKeyboardButton(text="🎯 Выбрать комнату", callback_data="admin_action_select_room")],
            [InlineKeyboardButton(text="📊 Статус выбранной комнаты", callback_data="admin_action_status")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_cancel")]
        ])
        await callback.message.edit_text("📋 <b>Управление комнатами</b>", reply_markup=kb, parse_mode="HTML")
        
    elif menu == "game":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛑 Принудительно завершить", callback_data="admin_action_force_end")],
            [InlineKeyboardButton(text="⏩ Пропустить ход игрока", callback_data="admin_action_skip")],
            [InlineKeyboardButton(text="🚪 Удалить игрока", callback_data="admin_action_remove")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_cancel")]
        ])
        await callback.message.edit_text("🎮 <b>Управление игрой</b> (применяется к выбранной комнате)", reply_markup=kb, parse_mode="HTML")
        
    elif menu == "eco":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Начислить монеты", callback_data="admin_action_add_coins")],
            [InlineKeyboardButton(text="➖ Забрать монеты", callback_data="admin_action_remove_coins")],
            [InlineKeyboardButton(text="✏️ Установить баланс", callback_data="admin_action_set_coins")],
            [InlineKeyboardButton(text="👑 Выдать титул", callback_data="admin_action_give_title")],
            [InlineKeyboardButton(text="🔄 Обнулить статистику", callback_data="admin_action_reset_stats")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_cancel")]
        ])
        await callback.message.edit_text("💰 <b>Экономика</b>", reply_markup=kb, parse_mode="HTML")
        
    elif menu == "surprises":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Запустить лотерею", callback_data="admin_action_lottery")],
            [InlineKeyboardButton(text="📢 Отправить объявление", callback_data="admin_action_shout")],
            [InlineKeyboardButton(text="🎰 Выбрать случайную игру", callback_data="admin_action_random_game")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_cancel")]
        ])
        await callback.message.edit_text("🎉 <b>Сюрпризы</b>", reply_markup=kb, parse_mode="HTML")
        
    elif menu == "admins":
        if not await is_main_admin(callback.from_user.id): return await callback.answer("⛔ Только для главного админа.", show_alert=True)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 Список админов", callback_data="admin_action_list_admins")],
            [InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_action_add_admin")],
            [InlineKeyboardButton(text="➖ Удалить админа", callback_data="admin_action_remove_admin")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_cancel")]
        ])
        await callback.message.edit_text("👥 <b>Управление администраторами</b>", reply_markup=kb, parse_mode="HTML")

# --- Обработка кнопок действий ---
@admin_router.callback_query(F.data.startswith("admin_action_"))
async def process_actions(callback: CallbackQuery, state: FSMContext, bot: Bot):
    action = callback.data.replace("admin_action_", "")
    user_id = callback.from_user.id
    chat_id = admin_selected_rooms.get(user_id)
    
    # Быстрые действия без ввода
    if action == "show_rooms":
        async with get_db() as db:
            async with db.execute("SELECT chat_id, game_type, players FROM games") as cursor:
                rows = await cursor.fetchall()
        if not rows: return await callback.answer("Нет активных комнат с играми.", show_alert=True)
        text = "📋 <b>Активные комнаты:</b>\n"
        for i, (cid, game_type, players_json) in enumerate(rows, 1):
            try:
                p_count = len([p for p in json.loads(players_json) if p.get('user_id') != bot.id])
                text += f"{i}. Чат (ID: <code>{cid}</code>) — Игроков: {p_count}, Игра: {game_type}\n"
            except: pass
        await callback.message.edit_text(text, reply_markup=get_cancel_kb(), parse_mode="HTML")
        
    elif action == "status":
        if not chat_id: return await callback.answer("Сначала выберите комнату!", show_alert=True)
        game = await get_game(chat_id)
        if not game: return await callback.answer("В этой комнате нет игры.", show_alert=True)
        players = [p['name'] for p in game['players'] if p['user_id'] != bot.id]
        text = (f"📊 <b>Статус комнаты {chat_id}</b>\nИгра: {game['game_type']}\nСостояние: {game['state']}\nИгроки: {', '.join(players)}")
        await callback.message.edit_text(text, reply_markup=get_cancel_kb(), parse_mode="HTML")
        
    elif action == "force_end":
        if not chat_id: return await callback.answer("Сначала выберите комнату!", show_alert=True)
        game = await get_game(chat_id)
        if game:
            await delete_game(chat_id)
            try: await bot.send_message(chat_id, "🛑 <b>Администратор принудительно завершил игру.</b>", parse_mode="HTML")
            except: pass
            await callback.answer("Игра завершена.", show_alert=True)
        else: await callback.answer("В этой комнате нет игры.", show_alert=True)
        
    elif action == "random_game":
        if not chat_id: return await callback.answer("Сначала выберите комнату!", show_alert=True)
        game = await get_game(chat_id)
        if not game or game['state'] != "selecting": return await callback.answer("Случайную игру можно запустить только при выборе игры.", show_alert=True)
        games = ["rps", "ttt", "dice", "slots", "roulette", "diamond", "race"]
        selected = random.choice(games)
        try: await bot.send_message(chat_id, f"🎲 <b>Администратор запустил случайную игру: {selected.upper()}!</b>", parse_mode="HTML")
        except: pass
        await callback.answer(f"Случайная игра ({selected}) объявлена.", show_alert=True)
        
    elif action == "list_admins":
        async with get_db() as db:
            async with db.execute("SELECT user_id, username, level FROM admins") as cursor:
                rows = await cursor.fetchall()
        text = "👥 <b>Список администраторов:</b>\n\n"
        for uid, uname, lvl in rows:
            text += f"• {uname} (<code>{uid}</code>) — {'Главный' if lvl == 2 else 'Обычный'}\n"
        await callback.message.edit_text(text, reply_markup=get_cancel_kb(), parse_mode="HTML")
        
    # Действия с вводом данных (FSM)
    elif action == "select_room":
        await state.set_state(AdminStates.waiting_for_select_room)
        await callback.message.edit_text("🎯 Введите ID комнаты (чата):", reply_markup=get_cancel_kb())
        
    elif action == "skip":
        await state.set_state(AdminStates.waiting_for_skip_user)
        await callback.message.edit_text("⏩ Введите @username игрока, чей ход нужно пропустить:", reply_markup=get_cancel_kb())
        
    elif action == "remove":
        await state.set_state(AdminStates.waiting_for_remove_user)
        await callback.message.edit_text("🚪 Введите @username игрока, которого нужно удалить из игры:", reply_markup=get_cancel_kb())
        
    elif action == "add_coins":
        if not await is_main_admin(user_id): return await callback.answer("⛔ Только для главного админа.", show_alert=True)
        await state.set_state(AdminStates.waiting_for_add_coins)
        await callback.message.edit_text("➕ Введите @username и сумму через пробел (например: Ivan 500):", reply_markup=get_cancel_kb())
        
    elif action == "remove_coins":
        if not await is_main_admin(user_id): return await callback.answer("⛔ Только для главного админа.", show_alert=True)
        await state.set_state(AdminStates.waiting_for_remove_coins)
        await callback.message.edit_text("➖ Введите @username и сумму через пробел (например: Ivan 200):", reply_markup=get_cancel_kb())
        
    elif action == "set_coins":
        if not await is_main_admin(user_id): return await callback.answer("⛔ Только для главного админа.", show_alert=True)
        await state.set_state(AdminStates.waiting_for_set_coins)
        await callback.message.edit_text("✏️ Введите @username и новый баланс (например: Ivan 1000):", reply_markup=get_cancel_kb())
        
    elif action == "give_title":
        if not await is_main_admin(user_id): return await callback.answer("⛔ Только для главного админа.", show_alert=True)
        await state.set_state(AdminStates.waiting_for_give_title)
        await callback.message.edit_text("👑 Введите @username и титул через пробел (например: Ivan Король):", reply_markup=get_cancel_kb())
        
    elif action == "reset_stats":
        if not await is_main_admin(user_id): return await callback.answer("⛔ Только для главного админа.", show_alert=True)
        await state.set_state(AdminStates.waiting_for_reset_stats)
        await callback.message.edit_text("🔄 Введите @username игрока для обнуления статистики:", reply_markup=get_cancel_kb())
        
    elif action == "shout":
        if not chat_id: return await callback.answer("Сначала выберите комнату!", show_alert=True)
        await state.set_state(AdminStates.waiting_for_shout)
        await callback.message.edit_text("📢 Введите текст объявления для выбранной комнаты:", reply_markup=get_cancel_kb())
        
    elif action == "lottery":
        if not chat_id: return await callback.answer("Сначала выберите комнату!", show_alert=True)
        await state.set_state(AdminStates.waiting_for_lottery)
        await callback.message.edit_text("🎲 Введите сумму выигрыша в лотерее (например: 100):", reply_markup=get_cancel_kb())
        
    elif action == "add_admin":
        if not await is_main_admin(user_id): return await callback.answer("⛔ Только для главного админа.", show_alert=True)
        await state.set_state(AdminStates.waiting_for_add_admin)
        await callback.message.edit_text("➕ Введите user_id нового администратора:", reply_markup=get_cancel_kb())
        
    elif action == "remove_admin":
        if not await is_main_admin(user_id): return await callback.answer("⛔ Только для главного админа.", show_alert=True)
        await state.set_state(AdminStates.waiting_for_remove_admin)
        await callback.message.edit_text("➖ Введите user_id администратора для удаления:", reply_markup=get_cancel_kb())

# --- Обработчики ввода FSM ---
@admin_router.message(StateFilter(AdminStates.waiting_for_select_room))
async def state_select_room(message: Message, state: FSMContext):
    chat_id_str = message.text.replace("-", "")
    if not chat_id_str.isdigit(): return await message.answer("❌ ID чата должен быть числом. Попробуйте еще раз или нажмите Отмена.", reply_markup=get_cancel_kb())
    admin_selected_rooms[message.from_user.id] = int(message.text)
    await state.clear()
    await message.answer(f"✅ Комната <code>{message.text}</code> выбрана.", reply_markup=get_main_menu_kb(), parse_mode="HTML")

@admin_router.message(StateFilter(AdminStates.waiting_for_skip_user))
async def state_skip(message: Message, state: FSMContext, bot: Bot):
    chat_id = admin_selected_rooms.get(message.from_user.id)
    if not chat_id:
        await state.clear()
        return await message.answer("⚠️ Выберите комнату в меню.", reply_markup=get_main_menu_kb())
    target_name = message.text.replace("@", "")
    game = await get_game(chat_id)
    if not game: return await message.answer("В комнате нет игры.", reply_markup=get_cancel_kb())
    
    target_user = next((p for p in game['players'] if p['name'] == target_name or p.get('username') == target_name), None)
    if not target_user: return await message.answer(f"Игрок '{target_name}' не найден в текущей игре.", reply_markup=get_cancel_kb())
    
    target_user['timeouts'] = target_user.get('timeouts', 0) + 1
    await save_game(game)
    try: await bot.send_message(chat_id, f"⏩ Администратор пропустил ход игрока <b>{target_user['name']}</b>.", parse_mode="HTML")
    except: pass
    await state.clear()
    await message.answer(f"✅ Ход {target_user['name']} пропущен.", reply_markup=get_main_menu_kb())

@admin_router.message(StateFilter(AdminStates.waiting_for_remove_user))
async def state_remove(message: Message, state: FSMContext, bot: Bot):
    chat_id = admin_selected_rooms.get(message.from_user.id)
    if not chat_id:
        await state.clear()
        return await message.answer("⚠️ Выберите комнату.", reply_markup=get_main_menu_kb())
    target_name = message.text.replace("@", "")
    game = await get_game(chat_id)
    if not game: return await message.answer("В комнате нет игры.", reply_markup=get_cancel_kb())
    
    target_user = next((p for p in game['players'] if p['name'] == target_name or p.get('username') == target_name), None)
    if not target_user: return await message.answer(f"Игрок '{target_name}' не найден в текущей игре.", reply_markup=get_cancel_kb())
    
    game['players'] = [p for p in game['players'] if p['user_id'] != target_user['user_id']]
    await save_game(game)
    try: await bot.send_message(chat_id, f"🚪 Игрок <b>{target_user['name']}</b> удален администратором.", parse_mode="HTML")
    except: pass
    await state.clear()
    await message.answer(f"✅ Игрок {target_user['name']} удалён.", reply_markup=get_main_menu_kb())

@admin_router.message(StateFilter(AdminStates.waiting_for_add_coins))
async def state_add_coins(message: Message, state: FSMContext, bot: Bot):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit(): 
        return await message.answer("❌ Ошибка: Вы забыли указать число или ввели неверный формат. Попробуйте снова (например: @username 500).", reply_markup=get_cancel_kb())
    target_name, amount = args[0].replace("@", ""), int(args[1])
    
    async with get_db() as db:
        async with db.execute("SELECT user_id, name, last_chat_id FROM users WHERE username = ? OR name = ?", (target_name, target_name)) as cursor:
            row = await cursor.fetchone()
        if not row: return await message.answer(f"❌ Игрок '{target_name}' не найден в БД.", reply_markup=get_cancel_kb())
        
        target_uid, actual_name, last_chat_id = row
        await db.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, target_uid))
        await db.commit()
        
    await log_admin_action(message.from_user.id, message.from_user.username or "Admin", "add_coins", actual_name, details=str(amount))
    chat_id = admin_selected_rooms.get(message.from_user.id) or last_chat_id
    if chat_id:
        try: await bot.send_message(chat_id, f"💰 Администрация начислила <b>{amount}</b> монет игроку <b>{actual_name}</b>!", parse_mode="HTML")
        except: pass
    await state.clear()
    await message.answer(f"✅ Начислено {amount} монет игроку {actual_name}.", reply_markup=get_main_menu_kb())

@admin_router.message(StateFilter(AdminStates.waiting_for_remove_coins))
async def state_remove_coins(message: Message, state: FSMContext):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit(): 
        return await message.answer("❌ Ошибка: Вы забыли указать число. Попробуйте снова (например: @username 200).", reply_markup=get_cancel_kb())
    target_name, amount = args[0].replace("@", ""), int(args[1])
    
    async with get_db() as db:
        async with db.execute("SELECT user_id, name, last_chat_id FROM users WHERE username = ? OR name = ?", (target_name, target_name)) as cursor:
            row = await cursor.fetchone()
        if not row: return await message.answer(f"❌ Игрок '{target_name}' не найден в БД.", reply_markup=get_cancel_kb())
        
        target_uid, actual_name, last_chat_id = row
        await db.execute("UPDATE users SET coins = MAX(0, coins - ?) WHERE user_id = ?", (amount, target_uid))
        await db.commit()
        
    await log_admin_action(message.from_user.id, message.from_user.username or "Admin", "remove_coins", actual_name, details=str(amount))
    await state.clear()
    await message.answer(f"✅ Снято {amount} монет у {actual_name}.", reply_markup=get_main_menu_kb())
    
    chat_id = admin_selected_rooms.get(message.from_user.id) or last_chat_id
    if chat_id:
        try: await bot.send_message(chat_id, f"➖ Администрация сняла <b>{amount}</b> монет у игрока <b>{actual_name}</b>.", parse_mode="HTML")
        except: pass

@admin_router.message(StateFilter(AdminStates.waiting_for_set_coins))
async def state_set_coins(message: Message, state: FSMContext):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit(): 
        return await message.answer("❌ Ошибка: Вы забыли указать число. Попробуйте снова (например: @username 1000).", reply_markup=get_cancel_kb())
    target_name, amount = args[0].replace("@", ""), int(args[1])
    
    async with get_db() as db:
        async with db.execute("SELECT user_id, name, last_chat_id FROM users WHERE username = ? OR name = ?", (target_name, target_name)) as cursor:
            row = await cursor.fetchone()
        if not row: return await message.answer(f"❌ Игрок '{target_name}' не найден в БД.", reply_markup=get_cancel_kb())
        
        target_uid, actual_name, last_chat_id = row
        await db.execute("UPDATE users SET coins = ? WHERE user_id = ?", (amount, target_uid))
        await db.commit()
        
    await log_admin_action(message.from_user.id, message.from_user.username or "Admin", "set_coins", actual_name, details=str(amount))
    await state.clear()
    await message.answer(f"✅ Баланс {actual_name} установлен в {amount}.", reply_markup=get_main_menu_kb())

@admin_router.message(StateFilter(AdminStates.waiting_for_give_title))
async def state_give_title(message: Message, state: FSMContext):
    args = message.text.split(" ", 1)
    if len(args) < 2: return await message.answer("❌ Формат: @username Босс", reply_markup=get_cancel_kb())
    target_name, title = args[0].replace("@", ""), args[1].strip('"')
    
    async with get_db() as db:
        async with db.execute("SELECT user_id, name, last_chat_id FROM users WHERE username = ? OR name = ?", (target_name, target_name)) as cursor:
            row = await cursor.fetchone()
        if not row: return await message.answer(f"❌ Игрок '{target_name}' не найден в БД.", reply_markup=get_cancel_kb())
        
        target_uid, actual_name, last_chat_id = row
        await db.execute("UPDATE users SET title = ? WHERE user_id = ?", (title, target_uid))
        await db.commit()
        
    await log_admin_action(message.from_user.id, message.from_user.username or "Admin", "give_title", actual_name, details=title)
    await state.clear()
    await message.answer(f"✅ Игроку {actual_name} выдан титул: {title}.", reply_markup=get_main_menu_kb())
    
    chat_id = admin_selected_rooms.get(message.from_user.id) or last_chat_id
    if chat_id:
        try: await bot.send_message(chat_id, f"👑 Администрация выдала особый титул <b>«{title}»</b> игроку <b>{actual_name}</b>!", parse_mode="HTML")
        except: pass

@admin_router.message(StateFilter(AdminStates.waiting_for_reset_stats))
async def state_reset_stats(message: Message, state: FSMContext):
    target_name = message.text.replace("@", "")
    
    async with get_db() as db:
        async with db.execute("SELECT user_id, name FROM users WHERE username = ? OR name = ?", (target_name, target_name)) as cursor:
            row = await cursor.fetchone()
        if not row: return await message.answer(f"❌ Игрок '{target_name}' не найден в БД.", reply_markup=get_cancel_kb())
        
        target_uid, actual_name = row
        await db.execute("UPDATE users SET games_played = 0, wins = 0, coins = 100, title = 'Новичок', played_games = '{}' WHERE user_id = ?", (target_uid,))
        await db.commit()
        
    await log_admin_action(message.from_user.id, message.from_user.username or "Admin", "reset_stats", actual_name)
    await state.clear()
    await message.answer(f"✅ Статистика {actual_name} обнулена.", reply_markup=get_main_menu_kb())

@admin_router.message(StateFilter(AdminStates.waiting_for_shout))
async def state_shout(message: Message, state: FSMContext, bot: Bot):
    chat_id = admin_selected_rooms.get(message.from_user.id)
    if not chat_id:
        await state.clear()
        return await message.answer("⚠️ Выберите комнату.", reply_markup=get_main_menu_kb())
    try:
        await bot.send_message(chat_id, f"📢 <b>Объявление от администрации:</b>\n{message.text}", parse_mode="HTML")
        await log_admin_action(message.from_user.id, message.from_user.username or "Admin", "shout", target_chat=chat_id, details=message.text)
        await state.clear()
        await message.answer("✅ Сообщение отправлено.", reply_markup=get_main_menu_kb())
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}", reply_markup=get_cancel_kb())

@admin_router.message(StateFilter(AdminStates.waiting_for_lottery))
async def state_lottery(message: Message, state: FSMContext, bot: Bot):
    chat_id = admin_selected_rooms.get(message.from_user.id)
    if not chat_id:
        await state.clear()
        return await message.answer("⚠️ Выберите комнату.", reply_markup=get_main_menu_kb())
    if not message.text.isdigit(): return await message.answer("❌ Укажите число (например: 100).", reply_markup=get_cancel_kb())
    amount = int(message.text)
    game = await get_game(chat_id)
    if not game or len(game['players']) < 2: return await message.answer("❌ Нужна активная игра.", reply_markup=get_cancel_kb())
    real_players = [p for p in game['players'] if p['user_id'] != bot.id]
    if not real_players: return await message.answer("❌ Нет реальных игроков.", reply_markup=get_cancel_kb())
    winner = random.choice(real_players)
    async with get_db() as db:
        await db.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, winner['user_id']))
        await db.commit()
    try:
        await bot.send_message(chat_id, f"🎉 <b>ЛОТЕРЕЯ!</b> 🎉\nСлучайный игрок <b>{winner['name']}</b> получает <b>{amount}</b> монет!", parse_mode="HTML")
        await log_admin_action(message.from_user.id, message.from_user.username or "Admin", "lottery", str(winner['user_id']), chat_id, str(amount))
        await state.clear()
        await message.answer(f"✅ Лотерея проведена. Победил {winner['name']}.", reply_markup=get_main_menu_kb())
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=get_cancel_kb())

@admin_router.message(StateFilter(AdminStates.waiting_for_add_admin))
async def state_add_admin(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("❌ Укажите user_id (число).", reply_markup=get_cancel_kb())
    target_id = int(message.text)
    async with get_db() as db:
        await db.execute('''
            INSERT OR REPLACE INTO admins (user_id, username, level, added_by)
            VALUES (?, ?, 1, ?)
        ''', (target_id, f"User{target_id}", message.from_user.id))
        await db.commit()
    await log_admin_action(message.from_user.id, message.from_user.username or "Admin", "add_admin", str(target_id))
    import menu
    await menu.set_admin_commands(bot, target_id)
    await state.clear()
    await message.answer(f"✅ Пользователь {target_id} назначен администратором и получил админское меню команд.", reply_markup=get_main_menu_kb())

@admin_router.message(StateFilter(AdminStates.waiting_for_remove_admin))
async def state_remove_admin(message: Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit(): return await message.answer("❌ Укажите user_id (число).", reply_markup=get_cancel_kb())
    target_id = int(message.text)
    if target_id == message.from_user.id: return await message.answer("❌ Нельзя удалить самого себя.", reply_markup=get_cancel_kb())
    async with get_db() as db:
        await db.execute("DELETE FROM admins WHERE user_id = ?", (target_id,))
        await db.commit()
    await log_admin_action(message.from_user.id, message.from_user.username or "Admin", "remove_admin", str(target_id))
    import menu
    await menu.remove_admin_commands(bot, target_id)
    await state.clear()
    await message.answer(f"✅ Администратор с ID {target_id} удалён и лишен админских команд.", reply_markup=get_main_menu_kb())
