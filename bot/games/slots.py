import time
import random
from aiogram import Router, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from db import get_game, save_game, delete_game, update_stats
from helpers import edit_or_send_game, edit_or_send

slots_router = Router()

def generate_slot_roll():
    symbols = ["🍒", "🍋", "🍊", "🍉", "🔔", "💎"]
    result = [random.choice(symbols) for _ in range(3)]
    score = 0
    if result[0] == result[1] == result[2]:
        score = 100
        if result[0] == "💎": score = 500
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        score = 10
    else:
        score = 0
    return {"result": result, "score": score}

async def start_slots(bot: Bot, chat_id: int, game: dict):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Крутить слоты 🎰", callback_data="slots_roll")]
    ])
    await edit_or_send_game(bot, game, "🎰 Слоты\nНажмите кнопку чтобы крутить барабан:", reply_markup=kb)

@slots_router.callback_query(F.data == "slots_roll")
async def cb_slots_roll(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "playing_slots": 
        return await call.answer("Игра не найдена.", show_alert=True)
    
    if user_id not in [p["user_id"] for p in game["players"]]:
        return await call.answer("Вы не участвуете в игре!", show_alert=True)
        
    if str(user_id) in game["game_state"]["rolls"]:
        return await call.answer("Вы уже покрутили слоты!", show_alert=True)
        
    roll = generate_slot_roll()
    game["game_state"]["rolls"][str(user_id)] = roll
    game["last_action_time"] = time.time()
    
    if len(game["game_state"]["rolls"]) == len(game["players"]):
        await finish_slots(bot, chat_id, game)
    else:
        ready = len(game["game_state"]["rolls"])
        total = len(game["players"])
        await edit_or_send_game(bot, game, f"🎰 Слоты\nПокрутили: {ready}/{total}", reply_markup=call.message.reply_markup)
    await call.answer(f"Выпало: {''.join(roll['result'])}")

async def finish_slots(bot: Bot, chat_id: int, game: dict):
    rolls = game["game_state"]["rolls"]
    players = game["players"]
    
    results = []
    max_score = -1
    winners = []
    
    for p in players:
        uid = str(p["user_id"])
        r = rolls.get(uid, {"result": ["❌", "❌", "❌"], "score": -1})
        res_str = "".join(r["result"])
        score = r["score"]
        results.append(f"{p['name']}: {res_str} ({score} очков)")
        if score > max_score:
            max_score = score
            winners = [p["name"]]
        elif score == max_score and score != -1:
            winners.append(p["name"])
            
    text = "🎰 Результаты слотов:\n" + "\n".join(results) + "\n\n"
    if len(winners) == 1:
        text += f"🏆 Победитель: {winners[0]}!"
    elif len(winners) > 1:
        text += f"🤝 Ничья между: {', '.join(winners)}!"
    else:
        text += "Никто не выиграл :("
        
    await update_stats(bot.id, players, winners, game_type="slots")
    from db import add_history
    await add_history(chat_id, "slots", [p["name"] for p in players], winners)
    await edit_or_send(bot, chat_id, game["last_message_id"], text)
    
    from helpers import delete_after
    import asyncio
    asyncio.create_task(delete_after(bot, chat_id, game["last_message_id"], 5))
    await delete_game(chat_id)
