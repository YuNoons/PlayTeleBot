import asyncio
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from db import save_game

async def delete_last_message(bot: Bot, chat_id: int, message_id: int):
    """Удаляет предыдущее игровое сообщение для очистки чата"""
    if message_id:
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception:
            pass # Игнорируем ошибки

async def delete_after(bot: Bot, chat_id: int, message_id: int, delay: int):
    """Удаляет сообщение через заданное время (в секундах)"""
    if delay > 0:
        await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

async def edit_or_send(bot: Bot, chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode=None):
    """Пытается отредактировать сообщение. Если не вышло — шлет новое."""
    if message_id:
        try:
            msg = await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup, parse_mode=parse_mode)
            if isinstance(msg, Message):
                return msg.message_id
            return message_id
        except Exception as e:
            if "message is not modified" in str(e).lower():
                return message_id
            await delete_last_message(bot, chat_id, message_id)
            
    msg = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    return msg.message_id

async def edit_or_send_game(bot: Bot, game: dict, text: str, reply_markup=None, parse_mode=None):
    """Отправляет/редактирует сообщение и сразу обновляет game['last_message_id'] и game['last_text']"""
    chat_id = game["chat_id"]
    message_id = game["last_message_id"]
    
    if message_id:
        try:
            msg = await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup, parse_mode=parse_mode)
            if isinstance(msg, Message):
                game["last_message_id"] = msg.message_id
            game["last_text"] = text
            await save_game(game)
            return game["last_message_id"]
        except Exception as e:
            if "message is not modified" in str(e).lower():
                game["last_text"] = text
                await save_game(game)
                return message_id
            await delete_last_message(bot, chat_id, message_id)
            
    msg = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    game["last_message_id"] = msg.message_id
    game["last_text"] = text
    await save_game(game)
    return msg.message_id

def get_active_waiting_players(game: dict) -> list:
    """Возвращает список имен игроков, которых мы сейчас ждем"""
    state = game["state"]
    players = game["players"]
    
    if state == "waiting" or state == "selecting":
        return []
        
    elif state == "betting_roulette":
        ready = game["game_state"].get("ready", [])
        return [p["name"] for p in players if str(p["user_id"]) not in ready]
        
    elif state == "playing_rps":
        choices = game["game_state"].get("choices", {})
        return [p["name"] for p in players if str(p["user_id"]) not in choices]
        
    elif state == "playing_ttt":
        turn_id = game["game_state"].get("turn")
        return [p["name"] for p in players if p["user_id"] == turn_id]
        
    elif state == "playing_dice":
        rolls = game["game_state"].get("rolls", {})
        return [p["name"] for p in players if str(p["user_id"]) not in rolls]
        
    elif state == "playing_slots":
        rolls = game["game_state"].get("rolls", {})
        return [p["name"] for p in players if str(p["user_id"]) not in rolls]
        
    elif state == "playing_diamond":
        turn_id = game["game_state"].get("turn")
        return [p["name"] for p in players if p["user_id"] == turn_id]
        
    elif state == "playing_roulette":
        turn_id = game["game_state"].get("turn")
        return [p["name"] for p in players if p["user_id"] == turn_id]
        
    elif state == "playing_race":
        ready = game["game_state"].get("ready", [])
        return [p["name"] for p in players if str(p["user_id"]) not in ready]
        
    return []

def get_ttt_kb(board: list):
    symbols = {1: "❌", 2: "⭕️"}
    kb = []
    for i in range(3):
        row = []
        for j in range(3):
            idx = i*3 + j
            btn_text = symbols.get(board[idx], str(idx + 1))
            row.append(InlineKeyboardButton(text=btn_text, callback_data=f"ttt_{idx}"))
        kb.append(row)
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_diamond_kb(board: list):
    symbols = {0: "⬛", 1: "💨", 2: "💎"}
    kb = []
    for i in range(3):
        row = []
        for j in range(3):
            idx = i*3 + j
            row.append(InlineKeyboardButton(text=symbols[board[idx]], callback_data=f"diamond_{idx}"))
        kb.append(row)
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def get_game_reply_markup(bot: Bot, game: dict) -> Optional[InlineKeyboardMarkup]:
    state = game["state"]
    if state == "waiting":
        bot_info = await bot.get_me()
        invite_url = f"https://t.me/{bot_info.username}?start=invite"
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Присоединиться", callback_data="join_game"),
                InlineKeyboardButton(text="🚪 Выйти", callback_data="leave_game")
            ],
            [
                InlineKeyboardButton(text="🎲 Начать игру", callback_data="start_game"),
                InlineKeyboardButton(text="👤 Пригласить", url=invite_url)
            ]
        ])
    elif state == "selecting":
        if "Аркадный зал" in game.get("last_text", ""):
            return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎲 Кости", callback_data="select_dice")],
                [InlineKeyboardButton(text="🎰 Слоты", callback_data="select_slots")],
                [InlineKeyboardButton(text="💎 Поиск алмаза", callback_data="select_diamond")],
                [InlineKeyboardButton(text="🏎 Гонка", callback_data="select_race")],
                [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
            ])
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✊ Камень-ножницы-бумага", callback_data="select_rps")],
                [InlineKeyboardButton(text="❌ Крестики-нолики", callback_data="select_ttt")],
                [InlineKeyboardButton(text="🔫 Рулетка", callback_data="select_roulette")]
            ])
            bot_in_game = any(p["user_id"] == bot.id for p in game["players"])
            if len(game["players"]) == 1 and not bot_in_game:
                kb.inline_keyboard.append([InlineKeyboardButton(text="🤖 Играть с ботом", callback_data="select_bot")])
            return kb
    elif state == "betting_roulette":
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💵 Ставка: +", callback_data="roulette_toggle_bet"),
                InlineKeyboardButton(text="✅ Подтвердить ставку", callback_data="roulette_confirm_bet")
            ]
        ])
    elif state == "playing_rps":
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✊ Камень", callback_data="rps_rock"),
                InlineKeyboardButton(text="✌️ Ножницы", callback_data="rps_scissors"),
                InlineKeyboardButton(text="✋ Бумага", callback_data="rps_paper")
            ]
        ])
    elif state == "playing_ttt":
        return get_ttt_kb(game["game_state"]["board"])
    elif state == "playing_dice":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Бросить кубик 🎲", callback_data="dice_roll")]
        ])
    elif state == "playing_slots":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Крутить слоты 🎰", callback_data="slots_roll")]
        ])
    elif state == "playing_diamond":
        return get_diamond_kb(game["game_state"]["board"])
    elif state == "playing_roulette":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💥 Спустить курок", callback_data="roulette_shoot")]
        ])
    elif state == "playing_race":
        ready_cnt = len(game["game_state"].get("ready", []))
        total_cnt = len(game["players"])
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🏁 Газ в пол! ({ready_cnt}/{total_cnt})" if ready_cnt > 0 else "🏁 Газ в пол! 💨", callback_data="race_gas")]
        ])
    return None

