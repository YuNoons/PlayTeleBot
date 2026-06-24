import asyncio
import time
import random
from aiogram import Router, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from db import get_game, save_game, delete_game, update_stats
from helpers import edit_or_send_game, edit_or_send

race_router = Router()

def render_race_track(game: dict):
    lines = ["🏁 <b>Гоночный трек!</b> 🏁\n"]
    for p in game["players"]:
        pos = game["game_state"]["positions"].get(str(p["user_id"]), 0)
        track = "▪️" * pos + "🏎" + "▪️" * (12 - pos) + "🚩"
        if pos >= 12:
            track = "▪️" * 12 + "🚩🏎💨"
        lines.append(f"<b>{p['name']}</b>\n{track}")
    return "\n\n".join(lines)

async def start_race(bot: Bot, chat_id: int, game: dict):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏁 Газ в пол! 💨", callback_data="race_gas")]
    ])
    await edit_or_send_game(bot, game, render_race_track(game), reply_markup=kb, parse_mode="HTML")
    
    # Авто-ход бота
    if any(p["user_id"] == bot.id for p in game["players"]):
        if str(bot.id) not in game["game_state"]["ready"]:
            game["game_state"]["ready"].append(str(bot.id))
            await save_game(game)

@race_router.callback_query(F.data == "race_gas")
async def cb_race_gas(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "playing_race": 
        return await call.answer("Игра не найдена.", show_alert=True)
    
    if user_id not in [p["user_id"] for p in game["players"]]:
        return await call.answer("Вы не участвуете в гонке!", show_alert=True)
        
    if str(user_id) in game["game_state"]["ready"]:
        return await call.answer("Вы уже нажали газ! Ждем остальных.", show_alert=True)
        
    game["game_state"]["ready"].append(str(user_id))
    game["last_action_time"] = time.time()
    
    if len(game["game_state"]["ready"]) == len(game["players"]):
        await process_race_turn(bot, chat_id, game)
    else:
        await save_game(game)
        ready = len(game["game_state"]["ready"])
        total = len(game["players"])
        try:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"🏁 Газ в пол! ({ready}/{total})", callback_data="race_gas")]
            ])
            await call.message.edit_reply_markup(reply_markup=kb)
        except:
            pass
    await call.answer("Врррум! 💨")

async def process_race_turn(bot: Bot, chat_id: int, game: dict):
    # Двигаем машинки
    positions = game["game_state"]["positions"]
    for p in game["players"]:
        uid = str(p["user_id"])
        advance = random.randint(1, 3)
        positions[uid] = min(12, positions.get(uid, 0) + advance)
        
    game["game_state"]["ready"] = []
    
    # Проверяем финиш
    winners = []
    for uid, pos in positions.items():
        if pos >= 12:
            name = next(p["name"] for p in game["players"] if str(p["user_id"]) == uid)
            winners.append(name)
            
    if winners:
        await finish_race(bot, chat_id, game, winners)
    else:
        # Следующий ход
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏁 Газ в пол! 💨", callback_data="race_gas")]
        ])
        await edit_or_send_game(bot, game, render_race_track(game), reply_markup=kb, parse_mode="HTML")
        
        # Бот жмет кнопку автоматически
        if any(p["user_id"] == bot.id for p in game["players"]):
            await asyncio.sleep(1)
            game = await get_game(chat_id) # reload
            game["game_state"]["ready"].append(str(bot.id))
            if len(game["game_state"]["ready"]) == len(game["players"]):
                await process_race_turn(bot, chat_id, game)
            else:
                await save_game(game)

async def finish_race(bot: Bot, chat_id: int, game: dict, winners: list):
    text = render_race_track(game) + "\n\n"
    if len(winners) == 1:
        text += f"🏆 <b>Гонку выигрывает {winners[0]}!</b>"
    else:
        text += f"🤝 <b>Фотофиниш! Ничья между: {', '.join(winners)}!</b>"
        
    await update_stats(bot.id, game["players"], winners, game_type="race")
    from db import add_history
    await add_history(chat_id, "race", [p["name"] for p in game["players"]], winners)
    await edit_or_send(bot, chat_id, game["last_message_id"], text, parse_mode="HTML")
    
    from helpers import delete_after
    import asyncio
    asyncio.create_task(delete_after(bot, chat_id, game["last_message_id"], 5))
    await delete_game(chat_id)
