import time
import random
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from db import get_game, save_game, delete_game, update_stats, add_history
from helpers import edit_or_send_game, edit_or_send, delete_after

rps_router = Router()

async def start_rps(bot: Bot, chat_id: int, game: dict):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✊ Камень", callback_data="rps_rock"),
            InlineKeyboardButton(text="✌️ Ножницы", callback_data="rps_scissors"),
            InlineKeyboardButton(text="✋ Бумага", callback_data="rps_paper")
        ]
    ])
    await edit_or_send_game(bot, game, "✊✌️✋ Камень-ножницы-бумага!\nСделайте свой выбор:", reply_markup=kb)

@rps_router.callback_query(F.data.startswith("rps_"))
async def cb_rps_choice(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "playing_rps": 
        return await call.answer("Игра не найдена.", show_alert=True)
    
    if user_id not in [p["user_id"] for p in game["players"]]:
        return await call.answer("Вы не участвуете в игре!", show_alert=True)
        
    if str(user_id) in game["game_state"]["choices"]:
        return await call.answer("Вы уже сделали выбор!", show_alert=True)
        
    choice = call.data.split("_")[1]
    game["game_state"]["choices"][str(user_id)] = choice
    game["last_action_time"] = time.time()
    
    if len(game["game_state"]["choices"]) == len(game["players"]):
        await finish_rps(bot, chat_id, game)
    else:
        ready = len(game["game_state"]["choices"])
        total = len(game["players"])
        await edit_or_send_game(bot, game, f"✊✌️✋ Камень-ножницы-бумага!\nИгроки сделали выбор: {ready}/{total}", reply_markup=call.message.reply_markup)
    await call.answer("Выбор принят!")

async def finish_rps(bot: Bot, chat_id: int, game: dict):
    choices = game["game_state"]["choices"]
    players = game["players"]
    
    results = []
    emoji_map = {"rock": "✊", "scissors": "✌️", "paper": "✋"}
    
    for p in players:
        uid = str(p["user_id"])
        c = choices.get(uid, "rock")
        results.append(f"• {p['name']}: {emoji_map[c]}")
        
    text = "*🏆 Камень-ножницы-бумага*\n\n*Результаты:*\n" + "\n".join(results) + "\n\n"
    
    winners = []
    unique_choices = set(choices.values())
    if len(unique_choices) == 1 or len(unique_choices) == 3:
        text += "*Итог:* 🤝 Ничья!"
    else:
        if "rock" in unique_choices and "scissors" in unique_choices:
            winning_choice = "rock"
        elif "scissors" in unique_choices and "paper" in unique_choices:
            winning_choice = "scissors"
        else:
            winning_choice = "paper"
            
        winners = [p["name"] for p in players if choices.get(str(p["user_id"])) == winning_choice]
        if len(winners) == 1:
            text += f"*Победитель:* {winners[0]}! 🎉"
        else:
            text += f"*Победители:* {', '.join(winners)}! 🎉"
            
    await update_stats(bot.id, players, winners, game_type="rps")
    await add_history(chat_id, "rps", [p["name"] for p in players], winners)
    
    await edit_or_send(bot, chat_id, game["last_message_id"], text, parse_mode="Markdown")
    asyncio.create_task(delete_after(bot, chat_id, game["last_message_id"], 5))
    await delete_game(chat_id)
