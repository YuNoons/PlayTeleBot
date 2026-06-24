import asyncio
import time
import random
from aiogram import Router, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from db import get_game, save_game, delete_game, update_stats
from helpers import edit_or_send_game, edit_or_send, delete_last_message, delete_after, get_ttt_kb

ttt_router = Router()

def check_ttt_winner(board):
    lines = [
        [0,1,2], [3,4,5], [6,7,8],
        [0,3,6], [1,4,7], [2,5,8],
        [0,4,8], [2,4,6]
    ]
    for line in lines:
        if board[line[0]] != 0 and board[line[0]] == board[line[1]] == board[line[2]]:
            return board[line[0]]
    if 0 not in board:
        return -1
    return 0

async def start_ttt(bot: Bot, chat_id: int, game: dict):
    
    turn_user_id = game["game_state"]["turn"]
    turn_name = next(p["name"] for p in game["players"] if p["user_id"] == turn_user_id)
    
    kb = get_ttt_kb(game["game_state"]["board"])
    game["last_action_time"] = time.time()
    await edit_or_send_game(bot, game, f"❌ Крестики-нолики\nХод: {turn_name}", reply_markup=kb)
    
    if turn_user_id == bot.id:
        await asyncio.sleep(1)
        await ttt_bot_move(bot, chat_id, game)

async def ttt_bot_move(bot: Bot, chat_id: int, game: dict):
    board = game["game_state"]["board"]
    empty = [i for i, x in enumerate(board) if x == 0]
    if empty:
        move = random.choice(empty)
        await process_ttt_move(bot, chat_id, game, bot.id, move)

@ttt_router.callback_query(F.data.startswith("ttt_"))
async def cb_ttt_move(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "playing_ttt": 
        return await call.answer("Игра не найдена.", show_alert=True)
    
    if game["game_state"]["turn"] != user_id:
        return await call.answer("Сейчас не ваш ход!", show_alert=True)
        
    idx = int(call.data.split("_")[1])
    board = game["game_state"]["board"]
    
    if board[idx] != 0:
        return await call.answer("Эта клетка занята!", show_alert=True)
        
    await process_ttt_move(bot, chat_id, game, user_id, idx)
    await call.answer()

@ttt_router.message(F.text.regexp(r"^[1-9]$"))
async def msg_ttt_move(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    game = await get_game(chat_id)
    
    if not game or game["state"] != "playing_ttt":
        return
        
    if game["game_state"]["turn"] != user_id:
        msg = await message.answer("Сейчас не ваш ход!")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 3))
        asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 3))
        return
        
    idx = int(message.text) - 1
    board = game["game_state"]["board"]
    
    if board[idx] != 0:
        msg = await message.answer("Эта клетка уже занята!")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 3))
        asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 3))
        return
        
    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
    await process_ttt_move(bot, chat_id, game, user_id, idx)

async def process_ttt_move(bot: Bot, chat_id: int, game: dict, user_id: int, idx: int):
    board = game["game_state"]["board"]
    symbols = game["game_state"]["symbols"]
    
    symbol = symbols[str(user_id)]
    board[idx] = 1 if symbol == "X" else 2
    game["last_action_time"] = time.time()
    
    winner = check_ttt_winner(board)
    if winner != 0:
        board_symbols = {0: "⬜", 1: "❌", 2: "⭕️"}
        board_text = ""
        for i in range(3):
            board_text += "`" + " ".join(board_symbols[x] for x in board[i*3:i*3+3]) + "`\n"
            
        from db import add_history
        if winner == -1:
            text = f"*🏆 Крестики-нолики*\n\n{board_text}\n*Результат:* 🤝 Ничья!"
            await update_stats(bot.id, game["players"], [], game_type="ttt")
            await add_history(chat_id, "ttt", [p["name"] for p in game["players"]], [])
        else:
            win_name = next(p["name"] for p in game["players"] if p["user_id"] == user_id)
            symbol_char = "❌" if symbol == "X" else "⭕️"
            text = f"*🏆 Крестики-нолики*\n\n{board_text}\n*Победитель:* {win_name} ({symbol_char}) 🎉"
            await update_stats(bot.id, game["players"], [win_name], game_type="ttt")
            await add_history(chat_id, "ttt", [p["name"] for p in game["players"]], [win_name])
            
        await edit_or_send(bot, chat_id, game["last_message_id"], text, parse_mode="Markdown")
        asyncio.create_task(delete_after(bot, chat_id, game["last_message_id"], 5))
        await delete_game(chat_id)
        return
        
    next_user_id = next(p["user_id"] for p in game["players"] if p["user_id"] != user_id)
    game["game_state"]["turn"] = next_user_id
    next_name = next(p["name"] for p in game["players"] if p["user_id"] == next_user_id)
    
    await edit_or_send_game(bot, game, f"❌ Крестики-нолики\nХод: {next_name}", reply_markup=get_ttt_kb(board))
    
    if next_user_id == bot.id:
        await asyncio.sleep(1)
        await ttt_bot_move(bot, chat_id, game)
