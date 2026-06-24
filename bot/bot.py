import asyncio
import logging
import os
import random
import time
from aiogram import Bot, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import db
from db import get_db, get_game, save_game, delete_game
from helpers import (
    edit_or_send, edit_or_send_game, delete_last_message, delete_after,
    get_active_waiting_players, get_game_reply_markup
)

# Импорт роутеров и игровых функций
from handlers.common import common_router
from games.rps import rps_router, finish_rps
from games.ttt import ttt_router, process_ttt_move
from games.roulette import roulette_router, process_roulette_move, start_roulette, start_roulette_betting
from games.dice import dice_router, finish_dice
from games.slots import slots_router, finish_slots
from games.diamond import diamond_router, process_diamond_move
from games.race import race_router, process_race_turn, render_race_track
from handlers.admin import admin_router

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация диспетчера
from aiogram import BaseMiddleware

user_last_action = {}

class UserTrackingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = None
        chat = None
        if hasattr(event, "from_user") and event.from_user:
            user = event.from_user
        if hasattr(event, "chat") and event.chat:
            chat = event.chat
            
        if user and chat:
            # 1. Anti-spam (Throttling)
            current_time = time.time()
            if current_time - user_last_action.get(user.id, 0) < 1.0:
                return # Игнорируем спам
            user_last_action[user.id] = current_time
            
            try:
                from db import update_user_info, get_db, get_setting, get_admin_level
                from aiogram.types import CallbackQuery, Message
                
                # 2. Maintenance Mode
                maintenance = await get_setting("maintenance_mode", "false")
                if maintenance.lower() == "true":
                    if await get_admin_level(user.id) < 1:
                        if isinstance(event, Message):
                            await event.answer("Бот находится на техническом обслуживании. Пожалуйста, подождите.")
                        elif isinstance(event, CallbackQuery):
                            await event.answer("Бот находится на техническом обслуживании. Пожалуйста, подождите.", show_alert=True)
                        return
                        
                await update_user_info(user.id, user.full_name, user.username or "", chat.id if chat.type in ["group", "supergroup"] else 0)
                
                async with get_db() as conn:
                    async with conn.execute("SELECT is_banned, ban_until FROM users WHERE user_id = ?", (user.id,)) as cursor:
                        row = await cursor.fetchone()
                
                if row:
                    is_banned, ban_until = row
                    if is_banned == 1:
                        if isinstance(event, CallbackQuery):
                            await event.answer("🚫 Ваш аккаунт заблокирован администратором.", show_alert=True)
                        return # Stop processing event for banned users
                        
                    if ban_until and ban_until > current_time:
                        # 3. Timeout / Mute Logic
                        allowed_commands = ["/profile", "/shop", "/inventory", "/help", "/report"]
                        allowed_callbacks = ["shop", "inventory", "buy_"]
                        
                        is_allowed = False
                        if hasattr(event, "text") and event.text:
                            for cmd in allowed_commands:
                                if event.text.startswith(cmd):
                                    is_allowed = True
                                    break
                        elif hasattr(event, "data") and event.data:
                            for cb in allowed_callbacks:
                                if event.data.startswith(cb):
                                    is_allowed = True
                                    break
                                    
                        if not is_allowed:
                            remaining = int(ban_until - current_time)
                            hours = remaining // 3600
                            minutes = (remaining % 3600) // 60
                            time_str = f"{hours} часов {minutes} минут" if hours > 0 else f"{minutes} минут"
                            
                            msg_text = f"Вы временно отстранены от игр. Блокировка спадет через {time_str}."
                            if isinstance(event, Message):
                                await event.answer(msg_text)
                            elif isinstance(event, CallbackQuery):
                                await event.answer(msg_text, show_alert=True)
                            return
                            
            except Exception as e:
                logging.error(f"Failed to track user: {e}")
                
        return await handler(event, data)

dp = Dispatcher()
dp.message.middleware(UserTrackingMiddleware())
dp.callback_query.middleware(UserTrackingMiddleware())

# Регистрация всех роутеров
dp.include_router(common_router)
dp.include_router(rps_router)
dp.include_router(ttt_router)
dp.include_router(roulette_router)
dp.include_router(dice_router)
dp.include_router(slots_router)
dp.include_router(diamond_router)
dp.include_router(race_router)
dp.include_router(admin_router)

async def timeout_checker(bot: Bot):
    """Фоновая задача проверки таймаутов"""
    while True:
        await asyncio.sleep(5)
        if not db.db_ready:
            continue
        try:
            async with get_db() as conn:
                async with conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'") as cursor:
                    if not await cursor.fetchone():
                        continue
                async with conn.execute("SELECT chat_id FROM games") as cursor:
                    rows = await cursor.fetchall()
                    
            for row in rows:
                chat_id = row[0]
                game = await get_game(chat_id)
                if not game or game["state"] in ["waiting", "selecting"]:
                    continue
                    
                elapsed = int(time.time() - game["last_action_time"])
                
                # Получаем игроков, чьих действий мы ждем
                waiting_names = get_active_waiting_players(game)
                if not waiting_names:
                    continue
                names_str = ", ".join(waiting_names)
                
                if 15 <= elapsed < 30:
                    # Показываем таймер в сообщении
                    base_text = game.get("last_text", "")
                    if "\n\n⏳ Ждём" in base_text:
                        base_text = base_text.split("\n\n⏳ Ждём")[0]
                    if "\n\n⏰ Игрок" in base_text:
                        base_text = base_text.split("\n\n⏰ Игрок")[0]
                        
                    new_text = base_text + f"\n\n⏳ Ждём {names_str}... ({elapsed}/30 сек)"
                    kb = await get_game_reply_markup(bot, game)
                    
                    try:
                        await bot.edit_message_text(new_text, chat_id=chat_id, message_id=game["last_message_id"], reply_markup=kb, parse_mode="HTML")
                    except Exception as e:
                        if "message is not modified" not in str(e).lower():
                            logging.error(f"Error in timeout_checker edit: {e}")
                            
                elif elapsed >= 30:
                    # Добавляем кнопку пропуска хода
                    base_text = game.get("last_text", "")
                    if "\n\n⏳ Ждём" in base_text:
                        base_text = base_text.split("\n\n⏳ Ждём")[0]
                    if "\n\n⏰ Игрок" in base_text:
                        base_text = base_text.split("\n\n⏰ Игрок")[0]
                        
                    new_text = base_text + f"\n\n⏰ Игрок {names_str} задерживается! Любой другой участник может пропустить его ход."
                    kb = await get_game_reply_markup(bot, game)
                    if kb:
                        kb.inline_keyboard.append([InlineKeyboardButton(text="⏩ Пропустить ход", callback_data="skip_timeout_player")])
                    else:
                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="⏩ Пропустить ход", callback_data="skip_timeout_player")]
                        ])
                        
                    try:
                        await bot.edit_message_text(new_text, chat_id=chat_id, message_id=game["last_message_id"], reply_markup=kb, parse_mode="HTML")
                    except Exception as e:
                        if "message is not modified" not in str(e).lower():
                            logging.error(f"Error in timeout_checker edit (30s): {e}")
                            
        except Exception as e:
            logging.error(f"Ошибка в timeout_checker: {e}")

async def handle_timeout(bot: Bot, chat_id: int, game: dict):
    """Обрабатывает таймауты: пропускает ход или завершает игру"""
    timed_out_users = []
    current_state = game["state"]
    
    if current_state == "waiting":
        await edit_or_send(bot, chat_id, game["last_message_id"], "⏳ Время ожидания вышло. Игра отменена.")
        await delete_game(chat_id)
        return
        
    elif current_state == "selecting":
        await edit_or_send(bot, chat_id, game["last_message_id"], "⏳ Игру не выбрали. Отмена.")
        await delete_game(chat_id)
        return
        
    elif current_state == "betting_roulette":
        ready = game["game_state"].get("ready", [])
        for p in game["players"]:
            if str(p["user_id"]) not in ready and p["user_id"] != bot.id:
                timed_out_users.append(p)
                
    elif current_state == "playing_rps":
        choices = game["game_state"].get("choices", {})
        for p in game["players"]:
            if str(p["user_id"]) not in choices and p["user_id"] != bot.id:
                timed_out_users.append(p)
                
    elif current_state == "playing_ttt":
        turn_id = game["game_state"]["turn"]
        for p in game["players"]:
            if p["user_id"] == turn_id and p["user_id"] != bot.id:
                timed_out_users.append(p)
                
    elif current_state == "playing_dice":
        rolls = game["game_state"]["rolls"]
        for p in game["players"]:
            if str(p["user_id"]) not in rolls and p["user_id"] != bot.id:
                timed_out_users.append(p)
                
    elif current_state == "playing_slots":
        rolls = game["game_state"]["rolls"]
        for p in game["players"]:
            if str(p["user_id"]) not in rolls and p["user_id"] != bot.id:
                timed_out_users.append(p)
                
    elif current_state == "playing_diamond":
        turn_id = game["game_state"]["turn"]
        for p in game["players"]:
            if p["user_id"] == turn_id and p["user_id"] != bot.id:
                timed_out_users.append(p)
                
    elif current_state == "playing_roulette":
        turn_id = game["game_state"]["turn"]
        for p in game["players"]:
            if p["user_id"] == turn_id and p["user_id"] != bot.id:
                timed_out_users.append(p)
                
    elif current_state == "playing_race":
        ready = game["game_state"].get("ready", [])
        for p in game["players"]:
            if str(p["user_id"]) not in ready and p["user_id"] != bot.id:
                timed_out_users.append(p)
                
    if not timed_out_users:
        game["last_action_time"] = time.time()
        await save_game(game)
        return
        
    game["last_action_time"] = time.time()
    
    for u in timed_out_users:
        u["timeouts"] += 1
        name = u["name"]
        
        if u["timeouts"] >= 2:
            await edit_or_send(bot, chat_id, game["last_message_id"], f"🛑 Игрок {name} был исключен за бездействие (2 таймаута). Игра завершена.")
            await delete_game(chat_id)
            return
        else:
            msg = await bot.send_message(chat_id, f"⏳ Игрок {name} задерживается. Пропускаем ход...")
            asyncio.create_task(delete_after(bot, chat_id, msg.message_id, 10))
            
            if current_state == "betting_roulette":
                uid = str(u["user_id"])
                if uid not in game["game_state"]["ready"]:
                    game["game_state"]["ready"].append(uid)
            elif current_state == "playing_rps":
                game["game_state"]["choices"][str(u["user_id"])] = random.choice(["rock", "paper", "scissors"])
            elif current_state == "playing_ttt":
                board = game["game_state"]["board"]
                empty = [i for i, x in enumerate(board) if x == 0]
                if empty:
                    await process_ttt_move(bot, chat_id, game, u["user_id"], random.choice(empty))
                    return
            elif current_state == "playing_dice":
                game["game_state"]["rolls"][str(u["user_id"])] = 0
            elif current_state == "playing_slots":
                game["game_state"]["rolls"][str(u["user_id"])] = {"result": ["❌", "❌", "❌"], "score": -1}
            elif current_state == "playing_diamond":
                board = game["game_state"]["board"]
                empty = [i for i, x in enumerate(board) if x == 0]
                if empty:
                    await process_diamond_move(bot, chat_id, game, u["user_id"], random.choice(empty))
                    return
            elif current_state == "playing_roulette":
                await process_roulette_move(bot, chat_id, game, u["user_id"])
                return
            elif current_state == "playing_race":
                game["game_state"]["ready"].append(str(u["user_id"]))
                
    await save_game(game)
    
    if current_state == "betting_roulette":
        if len(game["game_state"]["ready"]) == len(game["players"]):
            # Списание коинов
            async with get_db() as conn:
                for p in game["players"]:
                    if p["user_id"] == bot.id:
                        continue
                    p_uid = str(p["user_id"])
                    p_bet = game["game_state"]["bets"].get(p_uid, 10)
                    await conn.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (p_bet, p["user_id"]))
                await conn.commit()
                
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
            await start_roulette_betting(bot, chat_id, game)
            
    elif current_state == "playing_rps":
        if len(game["game_state"]["choices"]) == len(game["players"]):
            await finish_rps(bot, chat_id, game)
        else:
            ready = len(game["game_state"]["choices"])
            total = len(game["players"])
            kb = await get_game_reply_markup(bot, game)
            await edit_or_send_game(bot, game, f"✊✌️✋ Камень-ножницы-бумага!\nИгроки сделали выбор: {ready}/{total}", kb)
            
    elif current_state == "playing_dice":
        if len(game["game_state"]["rolls"]) == len(game["players"]):
            await finish_dice(bot, chat_id, game)
        else:
            ready = len(game["game_state"]["rolls"])
            total = len(game["players"])
            kb = await get_game_reply_markup(bot, game)
            await edit_or_send_game(bot, game, f"🎲 Кости\nБросили кубик: {ready}/{total}", kb)
            
    elif current_state == "playing_slots":
        if len(game["game_state"]["rolls"]) == len(game["players"]):
            await finish_slots(bot, chat_id, game)
        else:
            ready = len(game["game_state"]["rolls"])
            total = len(game["players"])
            kb = await get_game_reply_markup(bot, game)
            await edit_or_send_game(bot, game, f"🎰 Слоты\nПокрутили: {ready}/{total}", kb)
            
    elif current_state == "playing_race":
        if len(game["game_state"]["ready"]) == len(game["players"]):
            await process_race_turn(bot, chat_id, game)
        else:
            kb = await get_game_reply_markup(bot, game)
            await edit_or_send_game(bot, game, render_race_track(game), kb)

async def metrics_loop():
    """Фоновая задача для периодического сбора метрик"""
    interval = int(os.getenv("METRICS_INTERVAL", 3600))
    logging.info(f"Запущен сбор метрик (интервал: {interval} сек.)")
    while True:
        await asyncio.sleep(interval)
        if db.db_ready:
            from db import capture_metrics
            await capture_metrics()

from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramAPIError

async def broadcast_loop(bot: Bot):
    """Фоновая задача для обработки очереди рассылок"""
    while True:
        await asyncio.sleep(60) # Проверяем раз в минуту
        if not db.db_ready:
            continue
            
        try:
            async with get_db() as conn:
                # Ищем задачу на рассылку
                async with conn.execute("SELECT id, message_text, image_path FROM broadcast_tasks WHERE status = 'pending' LIMIT 1") as cursor:
                    task = await cursor.fetchone()
                    
                if not task:
                    continue
                    
                task_id, message_text, image_path = task
                
                # Обновляем статус на processing
                await conn.execute("UPDATE broadcast_tasks SET status = 'processing' WHERE id = ?", (task_id,))
                await conn.commit()
                
                # Получаем всех пользователей
                async with conn.execute("SELECT user_id FROM users") as cursor:
                    users = await cursor.fetchall()
                    
            logging.info(f"Начинается рассылка #{task_id} для {len(users)} пользователей.")
            
            success_count = 0
            for (user_id,) in users:
                try:
                    if image_path and os.path.exists(image_path):
                        photo = FSInputFile(image_path)
                        await bot.send_photo(chat_id=user_id, photo=photo, caption=message_text, parse_mode="HTML")
                    else:
                        await bot.send_message(chat_id=user_id, text=message_text, parse_mode="HTML")
                    success_count += 1
                except TelegramAPIError as e:
                    logging.warning(f"Ошибка при отправке рассылки пользователю {user_id}: {e}")
                except Exception as e:
                    logging.error(f"Неизвестная ошибка при отправке пользователю {user_id}: {e}")
                
                # Задержка для предотвращения FloodWait
                await asyncio.sleep(0.05)
                
            # Завершаем задачу
            async with get_db() as conn:
                await conn.execute("UPDATE broadcast_tasks SET status = 'completed' WHERE id = ?", (task_id,))
                await conn.commit()
                
            logging.info(f"Рассылка #{task_id} завершена. Успешно отправлено: {success_count}/{len(users)}.")
            
        except Exception as e:
            logging.error(f"Ошибка в broadcast_loop: {e}")

async def main():
    # Загрузка конфигурации
    config = {}
    try:
        import json
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.warning("Файл config.json не найден. Используются переменные окружения.")
    except json.JSONDecodeError:
        logging.error("Ошибка чтения config.json. Проверьте формат файла.")

    token = os.getenv("BOT_TOKEN") or config.get("bot_token")
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        logging.error("Не указан токен бота! Укажите его в config.json или переменной окружения BOT_TOKEN.")
        return
        
    bot = Bot(token=token)
    
    # Инициализация БД
    await db.init_db(bot)
    
    # Настройка командного меню Telegram (для обычных юзеров и админов)
    import menu
    await menu.setup_all_commands(bot)
    
    # Запуск фонового чекера таймаутов
    asyncio.create_task(timeout_checker(bot))
    
    # Запуск фонового сбора метрик
    asyncio.create_task(metrics_loop())
    
    # Запуск фонового обработчика рассылок
    asyncio.create_task(broadcast_loop(bot))
    
    # Запуск API сервера в фоне (если не запущен панелью)
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("0.0.0.0", 8000))
            s.close()
            # Порт свободен, запускаем
            import uvicorn
            import sys
            api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bot-api"))
            if api_dir not in sys.path:
                sys.path.append(api_dir)
            from main import app as api_app
            
            config = uvicorn.Config(api_app, host="0.0.0.0", port=8000, log_level="warning")
            server = uvicorn.Server(config)
            asyncio.create_task(server.serve())
            logging.info("API сервер успешно запущен ботом на порту 8000.")
        except OSError:
            logging.info("Порт 8000 уже занят. API сервер уже работает (возможно, запущен панелью).")
    except Exception as e:
        logging.error(f"Не удалось запустить API сервер в фоне: {e}")
        
    logging.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
