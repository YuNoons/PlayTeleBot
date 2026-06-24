import time
import random
from aiogram import Router, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from db import get_game, save_game, delete_game, update_stats
from helpers import edit_or_send_game, edit_or_send

dice_router = Router()

async def start_dice(bot: Bot, chat_id: int, game: dict):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Бросить кубик 🎲", callback_data="dice_roll")]
    ])
    await edit_or_send_game(bot, game, "🎲 Кости\nНажмите кнопку чтобы бросить кубик:", reply_markup=kb)

@dice_router.callback_query(F.data == "dice_roll")
async def cb_dice_roll(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "playing_dice": 
        return await call.answer("Игра не найдена.", show_alert=True)
    
    if user_id not in [p["user_id"] for p in game["players"]]:
        return await call.answer("Вы не участвуете в игре!", show_alert=True)
        
    if str(user_id) in game["game_state"]["rolls"]:
        return await call.answer("Вы уже бросили кубик!", show_alert=True)
        
    roll = random.randint(1, 6)
    game["game_state"]["rolls"][str(user_id)] = roll
    game["last_action_time"] = time.time()
    
    if len(game["game_state"]["rolls"]) == len(game["players"]):
        await finish_dice(bot, chat_id, game)
    else:
        ready = len(game["game_state"]["rolls"])
        total = len(game["players"])
        await edit_or_send_game(bot, game, f"🎲 Кости\nБросили кубик: {ready}/{total}", reply_markup=call.message.reply_markup)
    await call.answer(f"Вы выбросили {roll}!")

async def finish_dice(bot: Bot, chat_id: int, game: dict):
    rolls = game["game_state"]["rolls"]
    players = game["players"]
    
    results = []
    max_roll = -1
    winners = []
    
    for p in players:
        uid = str(p["user_id"])
        r = rolls.get(uid, 0)
        results.append(f"{p['name']}: {r} 🎲")
        if r > max_roll:
            max_roll = r
            winners = [p["name"]]
        elif r == max_roll:
            winners.append(p["name"])
            
    text = "🎲 Результаты бросков:\n" + "\n".join(results) + "\n\n"
    if len(winners) == 1:
        text += f"🏆 Победитель: {winners[0]}!"
    else:
        text += f"🤝 Ничья между: {', '.join(winners)}!"
        
    await update_stats(bot.id, players, winners, game_type="dice")
    from db import add_history
    await add_history(chat_id, "dice", [p["name"] for p in players], winners)
    await edit_or_send(bot, chat_id, game["last_message_id"], text)
    
    from helpers import delete_after
    import asyncio
    asyncio.create_task(delete_after(bot, chat_id, game["last_message_id"], 5))
    await delete_game(chat_id)
