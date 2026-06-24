import asyncio
import time
import random
from aiogram import Router, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from db import get_game, save_game, delete_game, update_stats
from helpers import edit_or_send_game, edit_or_send, delete_last_message, get_diamond_kb

diamond_router = Router()

async def start_diamond(bot: Bot, chat_id: int, game: dict):
    
    turn_user_id = game["game_state"]["turn"]
    turn_name = next(p["name"] for p in game["players"] if p["user_id"] == turn_user_id)
    
    kb = get_diamond_kb(game["game_state"]["board"])
    game["last_action_time"] = time.time()
    await edit_or_send_game(bot, game, f"💎 Поиск алмаза\nХод: {turn_name}", reply_markup=kb)
    
    if turn_user_id == bot.id:
        await asyncio.sleep(1)
        await diamond_bot_move(bot, chat_id, game)

async def diamond_bot_move(bot: Bot, chat_id: int, game: dict):
    board = game["game_state"]["board"]
    empty = [i for i, x in enumerate(board) if x == 0]
    if empty:
        move = random.choice(empty)
        await process_diamond_move(bot, chat_id, game, bot.id, move)

@diamond_router.callback_query(F.data.startswith("diamond_"))
async def cb_diamond_move(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "playing_diamond": 
        return await call.answer("Игра не найдена.", show_alert=True)
    
    if game["game_state"]["turn"] != user_id:
        return await call.answer("Сейчас не ваш ход!", show_alert=True)
        
    idx = int(call.data.split("_")[1])
    board = game["game_state"]["board"]
    
    if board[idx] != 0:
        return await call.answer("Здесь уже искали!", show_alert=True)
        
    await process_diamond_move(bot, chat_id, game, user_id, idx)
    await call.answer()

async def process_diamond_move(bot: Bot, chat_id: int, game: dict, user_id: int, idx: int):
    board = game["game_state"]["board"]
    diamond_idx = game["game_state"]["diamond_idx"]
    
    game["last_action_time"] = time.time()
    
    if idx == diamond_idx:
        board[idx] = 2 # Diamond
        win_name = next(p["name"] for p in game["players"] if p["user_id"] == user_id)
        text = f"*💎 Поиск алмаза*\n\nУра! 🏆 {win_name} нашел алмаз!"
        
        await update_stats(bot.id, game["players"], [win_name], game_type="diamond")
        from db import add_history
        await add_history(chat_id, "diamond", [p["name"] for p in game["players"]], [win_name])
        await edit_or_send(bot, chat_id, game["last_message_id"], text, reply_markup=get_diamond_kb(board), parse_mode="Markdown")
        from helpers import delete_after
        asyncio.create_task(delete_after(bot, chat_id, game["last_message_id"], 5))
        await delete_game(chat_id)
        return
    else:
        board[idx] = 1 # Miss
        
    order = game["game_state"]["order"]
    current_idx = order.index(user_id)
    next_user_id = order[(current_idx + 1) % len(order)]
    game["game_state"]["turn"] = next_user_id
    next_name = next(p["name"] for p in game["players"] if p["user_id"] == next_user_id)
    
    await edit_or_send_game(bot, game, f"💎 Поиск алмаза\nПусто! 💨\nХод: {next_name}", reply_markup=get_diamond_kb(board))
    
    if next_user_id == bot.id:
        await asyncio.sleep(1)
        await diamond_bot_move(bot, chat_id, game)
