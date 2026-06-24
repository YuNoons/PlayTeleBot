import asyncio
import time
import random
from aiogram import Router, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from db import get_game, save_game, delete_game, update_stats, get_db
from helpers import edit_or_send_game, edit_or_send, delete_last_message

roulette_router = Router()

async def start_roulette_betting(bot: Bot, chat_id: int, game: dict):
    lines = ["🔫 <b>Русская рулетка: Ставки</b>\n"]
    for p in game["players"]:
        uid = str(p["user_id"])
        bet = game["game_state"]["bets"].get(uid, 10)
        is_ready = uid in game["game_state"]["ready"]
        ready_status = "✅ Готов" if is_ready else "⏳ Выбирает ставку"
        lines.append(f"👤 {p['name']}: {bet} 🪙 ({ready_status})")
    
    total_bank = sum(game["game_state"]["bets"].values())
    lines.append(f"\n💰 <b>Банк:</b> {total_bank} 🪙")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💵 Ставка: +", callback_data="roulette_toggle_bet"),
            InlineKeyboardButton(text="✅ Подтвердить ставку", callback_data="roulette_confirm_bet")
        ]
    ])
    
    await edit_or_send_game(bot, game, "\n".join(lines), reply_markup=kb, parse_mode="HTML")

@roulette_router.callback_query(F.data == "roulette_toggle_bet")
async def cb_roulette_toggle_bet(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "betting_roulette":
        return await call.answer("Игра не найдена.", show_alert=True)
    
    if user_id not in [p["user_id"] for p in game["players"]]:
        return await call.answer("Вы не участвуете в игре!", show_alert=True)
        
    uid = str(user_id)
    if uid in game["game_state"]["ready"]:
        return await call.answer("Вы уже подтвердили свою ставку!", show_alert=True)
        
    current_bet = game["game_state"]["bets"].get(uid, 10)
    next_bet = 50 if current_bet == 10 else (100 if current_bet == 50 else 10)
    
    async with get_db() as db:
        async with db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            
    player_coins = row[0] if row else 100
    
    if player_coins < next_bet:
        return await call.answer(f"Недостаточно монет для ставки {next_bet} 🪙! (У вас {player_coins} 🪙)", show_alert=True)
        
    game["game_state"]["bets"][uid] = next_bet
    game["last_action_time"] = time.time()
    
    await save_game(game)
    await start_roulette_betting(bot, chat_id, game)
    await call.answer(f"Ставка изменена на {next_bet} 🪙")

@roulette_router.callback_query(F.data == "roulette_confirm_bet")
async def cb_roulette_confirm_bet(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "betting_roulette":
        return await call.answer("Игра не найдена.", show_alert=True)
        
    if user_id not in [p["user_id"] for p in game["players"]]:
        return await call.answer("Вы не участвуете в игре!", show_alert=True)
        
    uid = str(user_id)
    if uid in game["game_state"]["ready"]:
        return await call.answer("Вы уже подтвердили ставку!", show_alert=True)
        
    bet = game["game_state"]["bets"].get(uid, 10)
    async with get_db() as db:
        async with db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
    player_coins = row[0] if row else 100
    if player_coins < bet:
        game["game_state"]["bets"][uid] = 10
        await save_game(game)
        await start_roulette_betting(bot, chat_id, game)
        return await call.answer("Недостаточно монет!", show_alert=True)
        
    game["game_state"]["ready"].append(uid)
    game["last_action_time"] = time.time()
    
    if any(p["user_id"] == bot.id for p in game["players"]):
        bot_uid = str(bot.id)
        if bot_uid not in game["game_state"]["ready"]:
            other_uid = next(str(p["user_id"]) for p in game["players"] if p["user_id"] != bot.id)
            other_bet = game["game_state"]["bets"].get(other_uid, 10)
            game["game_state"]["bets"][bot_uid] = other_bet
            game["game_state"]["ready"].append(bot_uid)
            
    all_ready = len(game["game_state"]["ready"]) == len(game["players"])
    
    if all_ready:
        async with get_db() as db:
            for p in game["players"]:
                if p["user_id"] == bot.id:
                    continue
                p_uid = str(p["user_id"])
                p_bet = game["game_state"]["bets"].get(p_uid, 10)
                await db.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (p_bet, p["user_id"]))
            await db.commit()
            
        game["state"] = "playing_roulette"
        players = game["players"]
        random.shuffle(players)
        
        total_bank = sum(game["game_state"]["bets"].values())
        
        game["game_state"] = {
            "bullet": random.randint(1, 6),
            "current_shot": 1,
            "turn": players[0]["user_id"],
            "order": [p["user_id"] for p in players],
            "bets": game["game_state"]["bets"],
            "bank": total_bank
        }
        await start_roulette(bot, chat_id, game)
    else:
        await save_game(game)
        await start_roulette_betting(bot, chat_id, game)
        
    await call.answer("Ставка подтверждена!")

async def start_roulette(bot: Bot, chat_id: int, game: dict):
    
    turn_user_id = game["game_state"]["turn"]
    turn_name = next(p["name"] for p in game["players"] if p["user_id"] == turn_user_id)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💥 Спустить курок", callback_data="roulette_shoot")]
    ])
    
    game["last_action_time"] = time.time()
    await edit_or_send_game(bot, game, f"🔫 Русская рулетка\nПатрон заряжен. Барабан раскручен.\nХод: {turn_name}", reply_markup=kb)
    
    if turn_user_id == bot.id:
        await asyncio.sleep(1.5)
        await process_roulette_move(bot, chat_id, game, bot.id)

@roulette_router.callback_query(F.data == "roulette_shoot")
async def cb_roulette_shoot(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "playing_roulette": 
        return await call.answer("Игра не найдена.", show_alert=True)
    
    if game["game_state"]["turn"] != user_id:
        return await call.answer("Сейчас не ваш ход!", show_alert=True)
        
    await process_roulette_move(bot, chat_id, game, user_id)
    await call.answer()

async def process_roulette_move(bot: Bot, chat_id: int, game: dict, user_id: int):
    current_shot = game["game_state"]["current_shot"]
    bullet = game["game_state"]["bullet"]
    game["last_action_time"] = time.time()
    
    shooter_name = next(p["name"] for p in game["players"] if p["user_id"] == user_id)
    
    if current_shot == bullet:
        # Выстрел! Игрок проиграл
        winners = [p["name"] for p in game["players"] if p["user_id"] != user_id]
        
        bank = game["game_state"].get("bank", 0)
        total_survivors = len(winners)
        
        if bank > 0 and total_survivors > 0:
            commission = int(bank * 0.20)
            net_bank = bank - commission
            coins_earned = net_bank // total_survivors
        else:
            commission = 0
            net_bank = 0
            coins_earned = 0
        
        coins_override = {}
        for p in game["players"]:
            if p["user_id"] == bot.id:
                continue
            if p["user_id"] != user_id:
                coins_override[p["user_id"]] = coins_earned
            else:
                coins_override[p["user_id"]] = 0
                
        text = f"🔫 Выстрел! 💥\nИгрок {shooter_name} выбывает!\n"
        if len(winners) > 0:
            text += f"🏆 Выжившие: {', '.join(winners)}!\nКаждый получает {coins_earned} 🪙 (раздел банка {net_bank} 🪙, комиссия 20%)"
            await update_stats(bot.id, game["players"], winners, coins_override=coins_override, game_type="roulette")
            from db import add_history
            await add_history(chat_id, "roulette", [p["name"] for p in game["players"]], winners)
        else:
            text += "Все проиграли!"
            await update_stats(bot.id, game["players"], [], coins_override=coins_override, game_type="roulette")
            from db import add_history
            await add_history(chat_id, "roulette", [p["name"] for p in game["players"]], [])
            
        await edit_or_send(bot, chat_id, game["last_message_id"], text)
        from helpers import delete_after
        asyncio.create_task(delete_after(bot, chat_id, game["last_message_id"], 5))
        await delete_game(chat_id)
        return
    else:
        # Щелчок
        game["game_state"]["current_shot"] += 1
        
        order = game["game_state"]["order"]
        current_idx = order.index(user_id)
        next_user_id = order[(current_idx + 1) % len(order)]
        game["game_state"]["turn"] = next_user_id
        next_name = next(p["name"] for p in game["players"] if p["user_id"] == next_user_id)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💥 Спустить курок", callback_data="roulette_shoot")]
        ])
        await edit_or_send_game(bot, game, f"🔫 Щелчок! Осечка. 😅\n{shooter_name} выжил.\n\nХод: {next_name}", reply_markup=kb)
        
        if next_user_id == bot.id:
            await asyncio.sleep(1.5)
            await process_roulette_move(bot, chat_id, game, bot.id)
