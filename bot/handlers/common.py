import asyncio
import time
import json
import random
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from db import get_game, save_game, delete_game, get_db
from helpers import edit_or_send, edit_or_send_game, delete_last_message, delete_after, get_active_waiting_players

common_router = Router()

@common_router.message(Command("help"))
async def cmd_help(message: Message, bot: Bot):
    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
    text = (
        "🤖 <b>Гайд по Игровому Боту</b>\n\n"
        "<b>Доступные команды:</b>\n"
        "/start — Создать комнату или войти в существующую\n"
        "/exit — Принудительно завершить игру в текущем чате\n"
        "/arcade — Войти в аркадный зал (доступно при выборе игр)\n"
        "/profile — Ваш профиль, баланс, винрейт и любимая игра\n"
        "/top — Топ-3 игроков компании\n"
        "/daily — Получить ежедневный бонус (раз в 24 часа)\n"
        "/shop — Магазин титулов и предметов\n"
        "/inventory — Ваш инвентарь покупок\n"
        "/help — Показать эту справку\n\n"
        "<b>Правила игр:</b>\n"
        "• ✊ Камень-ножницы-бумага: Стандартная игра, выигрывает сильнейший жест.\n"
        "• ❌ Крестики-нолики: Игроки ходят по очереди на поле 3х3. Кнопки пронумерованы от 1 до 9. Можно также отправлять цифры в чат.\n"
        "• 🔫 Русская рулетка: Игроки делают ставки (10, 50, 100 🪙). В барабане 1 патрон. Выжившие забирают весь банк поровну!"
    )
    msg = await message.answer(text, parse_mode="HTML")
    asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))

@common_router.message(Command("profile"))
async def cmd_profile(message: Message, bot: Bot):
    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
    user_id = message.from_user.id
    async with get_db() as db:
        async with db.execute("SELECT games_played, wins, coins, title, played_games FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            
    if row:
        games, wins, coins, title, played_games_json = row
        
        # Вычисление любимой игры
        fav_game = "Нет сыгранных игр"
        if played_games_json:
            try:
                played_games_dict = json.loads(played_games_json)
                if played_games_dict:
                    fav_game_key = max(played_games_dict, key=played_games_dict.get)
                    game_names = {
                        "rps": "✊ Камень-ножницы-бумага",
                        "ttt": "❌ Крестики-нолики",
                        "roulette": "🔫 Русская рулетка",
                        "dice": "🎲 Кости",
                        "slots": "🎰 Слоты",
                        "diamond": "💎 Поиск алмаза",
                        "race": "🏎 Гонка"
                    }
                    fav_game = game_names.get(fav_game_key, fav_game_key)
            except Exception:
                pass
                
        winrate = round(wins / games * 100) if games > 0 else 0
        text = (
            f"👤 <b>Профиль игрока:</b> {message.from_user.full_name}\n"
            f"🏅 <b>Титул:</b> {title}\n"
            f"💰 <b>Баланс:</b> {coins} 🪙\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"🎮 Сыграно игр: {games}\n"
            f"🏆 Побед: {wins}\n"
            f"🎯 Винрейт: {winrate}%\n"
            f"❤️ Любимая игра: {fav_game}"
        )
        msg = await message.answer(text, parse_mode="HTML")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))
    else:
        msg = await message.answer("У вас пока нет профиля. Начните игру с помощью /start!")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))

@common_router.message(Command("top"))
async def cmd_top(message: Message, bot: Bot):
    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
    chat_id = message.chat.id
    from db import get_history
    history = await get_history(chat_id, limit=50)
    players_in_chat = set()
    for h in history:
        players_in_chat.update(h["players"])
        
    async with get_db() as db:
        async with db.execute("SELECT name, title, wins, coins FROM users ORDER BY coins DESC, wins DESC") as cursor:
            rows = await cursor.fetchall()
            
    if players_in_chat:
        rows = [r for r in rows if r[0] in players_in_chat][:5]
    else:
        rows = rows[:3]
        
    if not rows:
        msg = await message.answer("Рейтинг пока пуст. Сыграйте первую игру!")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))
        return
        
    text = "🏆 <b>Командный рейтинг:</b>\n\n"
    for i, (name, title, wins, coins) in enumerate(rows):
        medal = ["🥇", "🥈", "🥉", "4.", "5."][i] if i < 3 else f"{i+1}."
        text += f"{medal} <b>{name}</b> [{title}] — {coins} 🪙 ({wins} побед)\n"
        
    msg = await message.answer(text, parse_mode="HTML")
    asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))

@common_router.message(Command("history"))
async def cmd_history(message: Message, bot: Bot):
    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
    from db import get_history
    history = await get_history(message.chat.id, limit=5)
    
    if not history:
        msg = await message.answer("В этом чате пока не было игр.")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))
        return
        
    game_names = {
        "rps": "✊ Камень-ножницы-бумага", "ttt": "❌ Крестики-нолики", 
        "roulette": "🔫 Русская рулетка", "dice": "🎲 Кости", 
        "slots": "🎰 Слоты", "diamond": "💎 Поиск алмаза", "race": "🏎 Гонка"
    }
    
    text = "📜 <b>История последних игр:</b>\n\n"
    for i, h in enumerate(history, 1):
        g_name = game_names.get(h["game_type"], h["game_type"])
        players_str = ", ".join(h["players"])
        winners_str = ", ".join(h["winners"]) if h["winners"] else "Ничья"
        text += f"{i}. <b>{g_name}</b>\n👥 {players_str}\n🏆 Победитель: {winners_str}\n\n"
        
    msg = await message.answer(text, parse_mode="HTML")
    asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 30))

@common_router.message(Command("daily"))
async def cmd_daily(message: Message, bot: Bot):
    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
    user_id = message.from_user.id
    async with get_db() as db:
        async with db.execute("SELECT last_daily, coins FROM users WHERE user_id=?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            
    if not row:
        msg = await message.answer("Сначала сыграйте хотя бы одну игру (/start), чтобы создать профиль!")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))
        return
        
    last_daily, coins = row
    now = time.time()
    
    if now - last_daily < 86400:
        hours_left = int((86400 - (now - last_daily)) // 3600)
        mins_left = int(((86400 - (now - last_daily)) % 3600) // 60)
        msg = await message.answer(f"⏳ Следующий бонус будет доступен через {hours_left} ч. {mins_left} мин.")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))
        return
        
    bonus = random.randint(100, 500)
    async with get_db() as db:
        await db.execute("UPDATE users SET coins = coins + ?, last_daily = ? WHERE user_id=?", (bonus, now, user_id))
        await db.commit()
        
    msg = await message.answer(f"🎁 Вы получили ежедневный бонус: <b>+{bonus} 🪙</b>!\nТеперь у вас: {coins + bonus} 🪙.", parse_mode="HTML")
    asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))

@common_router.message(Command("shop"))
async def cmd_shop(message: Message, bot: Bot):
    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
    from db import get_active_items
    items = await get_active_items()
    
    if not items:
        msg = await message.answer("🛒 <b>Магазин пока пуст.</b>\nЗагляните позже!", parse_mode="HTML")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))
        return
        
    text = "🛒 <b>Магазин товаров:</b>\n\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    for item in items:
        # Формируем красивое описание
        desc = f" ({item['description']})" if item['description'] else ""
        type_emoji = "🏅" if item['item_type'] == "title" else "📦"
        text += f"{type_emoji} <b>{item['name']}</b>{desc} — {item['price']} 🪙\n"
        
        # Добавляем инлайн кнопку
        kb.inline_keyboard.append(
            [InlineKeyboardButton(text=f"Купить {item['name']} ({item['price']} 🪙)", callback_data=f"buy_item_{item['id']}")]
        )
        
    text += "\n<i>Нажмите на кнопку ниже, чтобы приобрести товар!</i>"
    
    msg = await message.answer(text, reply_markup=kb, parse_mode="HTML")
    asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 30))

@common_router.callback_query(F.data.startswith("buy_item_"))
async def cb_buy_item(call: CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    item_id = int(call.data.split("_")[2])
    
    from db import buy_item
    success, msg_text = await buy_item(user_id, item_id)
    
    if success:
        await call.answer(msg_text, show_alert=True)
        # Отправляем радостное сообщение в чат
        msg = await call.message.answer(f"🎉 <b>{call.from_user.full_name}</b> успешно приобрел(а) товар из магазина!\n{msg_text}", parse_mode="HTML")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))
    else:
        await call.answer(msg_text, show_alert=True)

@common_router.message(Command("report"))
async def cmd_report(message: Message, bot: Bot):
    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
    args = message.text.split(maxsplit=2)
    
    if len(args) < 3:
        msg = await message.answer("⚠️ <b>Использование:</b>\n<code>/report [ID_пользователя] [причина]</code>\n\nПример:\n<code>/report 12345678 Читы в рулетке</code>", parse_mode="HTML")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))
        return
        
    try:
        target_id = int(args[1])
    except ValueError:
        msg = await message.answer("⚠️ ID пользователя должен быть числом.")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))
        return
        
    reason = args[2]
    
    from db import create_report
    await create_report(
        sender_id=message.from_user.id,
        sender_name=message.from_user.full_name,
        target_id=target_id,
        reason=reason
    )
    
    msg = await message.answer("✅ Ваша жалоба успешно отправлена администрации. Спасибо за помощь!")
    asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))

@common_router.message(Command("inventory"))
async def cmd_inventory(message: Message, bot: Bot):
    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
    from db import get_user_inventory
    user_id = message.from_user.id
    inventory = await get_user_inventory(user_id)
    
    if not inventory:
        msg = await message.answer("🎒 <b>Ваш инвентарь пуст.</b>\nЗагляните в /shop, чтобы купить что-нибудь!", parse_mode="HTML")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))
        return
        
    text = f"🎒 <b>Инвентарь игрока {message.from_user.full_name}:</b>\n\n"
    for idx, item in enumerate(inventory, 1):
        type_str = "Титул" if item["item_type"] == "title" else item["item_type"]
        text += f"{idx}. <b>{item['name']}</b> [{type_str}]\n"
        
    msg = await message.answer(text, parse_mode="HTML")
    asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 20))

@common_router.callback_query(F.data == "show_top")
async def cb_show_top(call: CallbackQuery, bot: Bot):
    async with get_db() as db:
        async with db.execute("SELECT name, title, wins, coins FROM users ORDER BY coins DESC, wins DESC LIMIT 3") as cursor:
            rows = await cursor.fetchall()
            
    if not rows:
        return await call.answer("Рейтинг пока пуст.", show_alert=True)
        
    text = "🏆 <b>Топ 3 компании:</b>\n\n"
    for i, (name, title, wins, coins) in enumerate(rows):
        medal = ["🥇", "🥈", "🥉"][i]
        text += f"{medal} <b>{name}</b> [{title}] — {coins} 🪙 ({wins} побед)\n"
        
    msg = await bot.send_message(call.message.chat.id, text, parse_mode="HTML")
    asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))
    await call.answer()

@common_router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    chat_id = message.chat.id
    game = await get_game(chat_id)
    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
    
    if game:
        if game["state"] == "waiting":
            msg = await message.answer("Комната уже создана! Нажмите «➕ Присоединиться» на сообщении выше 👆")
        else:
            msg = await message.answer("Идёт игра! Дождитесь окончания или нажмите /exit, чтобы выйти.")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 10))
        return
        
    players = [{"user_id": message.from_user.id, "name": message.from_user.full_name, "username": message.from_user.username or "", "timeouts": 0}]
    
    game = {
        "chat_id": chat_id,
        "players": players,
        "game_type": "",
        "game_state": {},
        "last_message_id": 0,
        "last_action_time": time.time(),
        "state": "waiting"
    }
    
    from helpers import get_game_reply_markup
    kb = await get_game_reply_markup(bot, game)
    players_text = ", ".join([p['name'] for p in game["players"]])
    text = f"🏢 <b>Корпоративная игровая комната</b>\n👥 В комнате: {players_text} ({len(game['players'])}/3)\n🎮 Выберите действие:"
    await edit_or_send_game(bot, game, text, kb, parse_mode="HTML")

@common_router.message(Command("exit"))
async def cmd_exit(message: Message, bot: Bot):
    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
    chat_id = message.chat.id
    game = await get_game(chat_id)
    if game:
        await delete_last_message(bot, chat_id, game["last_message_id"])
        await delete_game(chat_id)
        msg = await message.answer("🛑 Комната закрыта по инициативе игрока.")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 10))
    else:
        msg = await message.answer("В этом чате нет активной игры.")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 10))

@common_router.message(Command("rps", "dice", "ttt", "slots", "diamond", "race", "roulette"))
async def cmd_fast_game(message: Message, bot: Bot):
    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
    chat_id = message.chat.id
    game = await get_game(chat_id)
    command = message.text.split("@")[0].strip("/")
    
    if not game:
        game = {
            "chat_id": chat_id,
            "players": [{"user_id": message.from_user.id, "name": message.from_user.full_name, "username": message.from_user.username or "", "timeouts": 0}],
            "game_type": "",
            "game_state": {},
            "last_message_id": 0,
            "last_action_time": time.time(),
            "state": "waiting"
        }
    
    if game["state"] not in ["waiting", "selecting"]:
        msg = await message.answer("Сначала завершите текущую игру!")
        asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 10))
        return
        
    game["state"] = "selecting"
    game["game_type"] = command
    
    # Имитируем нажатие кнопки выбора игры
    class MockCall:
        def __init__(self):
            self.data = f"select_{command}"
            self.message = Message(message_id=0, date=message.date, chat=message.chat)
            self.from_user = message.from_user
        async def answer(self, *args, **kwargs):
            pass
            
    await save_game(game)
    await cb_select_game_type(MockCall(), bot)

@common_router.message(Command("arcade"))
async def cmd_arcade(message: Message, bot: Bot):
    chat_id = message.chat.id
    game = await get_game(chat_id)
    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
    
    if game:
        if game["state"] != "selecting":
            msg = await message.answer("Аркадный зал доступен только во время выбора игры.")
            asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 10))
            return
    else:
        players = [{"user_id": message.from_user.id, "name": message.from_user.full_name, "username": message.from_user.username or "", "timeouts": 0}]
        game = {
            "chat_id": chat_id,
            "players": players,
            "game_type": "",
            "game_state": {},
            "last_message_id": 0,
            "last_action_time": time.time(),
            "state": "selecting"
        }
        
    game["state"] = "selecting"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Кости", callback_data="select_dice")],
        [InlineKeyboardButton(text="🎰 Слоты", callback_data="select_slots")],
        [InlineKeyboardButton(text="💎 Поиск алмаза", callback_data="select_diamond")],
        [InlineKeyboardButton(text="🏎 Гонка", callback_data="select_race")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
    ])
    
    game["last_action_time"] = time.time()
    await edit_or_send_game(bot, game, "🎰 <b>Аркадный зал</b>\nВыберите скрытую игру:", reply_markup=kb, parse_mode="HTML")

@common_router.callback_query(F.data == "join_game")
async def cb_join_game(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "waiting":
        return await call.answer("Игра недоступна или уже началась.", show_alert=True)
        
    user_id = call.from_user.id
    
    if any(p["user_id"] == user_id for p in game["players"]):
        return await call.answer("Вы уже в игре!", show_alert=True)
        
    if len(game["players"]) >= 3:
        return await call.answer("Достигнуто максимальное количество игроков (3).", show_alert=True)
        
    game["players"].append({"user_id": user_id, "name": call.from_user.full_name, "username": call.from_user.username or "", "timeouts": 0})
    game["last_action_time"] = time.time()
    
    from helpers import get_game_reply_markup
    kb = await get_game_reply_markup(bot, game)
    players_text = ", ".join([p['name'] for p in game["players"]])
    text = f"🏢 <b>Корпоративная игровая комната</b>\n👥 В комнате: {players_text} ({len(game['players'])}/3)\n🎮 Выберите действие:"
    
    await edit_or_send_game(bot, game, text, kb, parse_mode="HTML")
    await call.answer("Вы присоединились!")

@common_router.callback_query(F.data == "leave_game")
async def cb_leave_game(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "waiting":
        return await call.answer("Нельзя выйти в данный момент.", show_alert=True)
        
    user_id = call.from_user.id
    if not any(p["user_id"] == user_id for p in game["players"]):
        return await call.answer("Вы не в игре.", show_alert=True)
        
    game["players"] = [p for p in game["players"] if p["user_id"] != user_id]
    if not game["players"]:
        await delete_game(chat_id)
        await delete_last_message(bot, chat_id, game["last_message_id"])
        return await call.answer("Комната закрыта.", show_alert=True)
        
    game["last_action_time"] = time.time()
    await save_game(game)
    from helpers import get_game_reply_markup
    kb = await get_game_reply_markup(bot, game)
    players_text = ", ".join([p['name'] for p in game["players"]])
    text = f"🏢 <b>Корпоративная игровая комната</b>\n👥 В комнате: {players_text} ({len(game['players'])}/3)\n🎮 Выберите действие:"
    await edit_or_send_game(bot, game, text, kb, parse_mode="HTML")
    await call.answer("Вы покинули комнату.")

@common_router.callback_query(F.data == "start_game")
async def cb_start_game(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "waiting": 
        return await call.answer("Игра недоступна.", show_alert=True)
        
    if call.from_user.id not in [p["user_id"] for p in game["players"]]:
        return await call.answer("Только участники могут начать игру.", show_alert=True)

    await show_game_menu(bot, chat_id, game)
    await call.answer()

async def show_game_menu(bot: Bot, chat_id: int, game: dict):
    game["state"] = "selecting"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✊ Камень-ножницы-бумага", callback_data="select_rps")],
        [InlineKeyboardButton(text="❌ Крестики-нолики", callback_data="select_ttt")],
        [InlineKeyboardButton(text="🔫 Рулетка", callback_data="select_roulette")]
    ])
    
    bot_in_game = any(p["user_id"] == bot.id for p in game["players"])
    if len(game["players"]) == 1 and not bot_in_game:
        kb.inline_keyboard.append([InlineKeyboardButton(text="🤖 Играть с ботом", callback_data="select_bot")])
        
    game["last_action_time"] = time.time()
    await edit_or_send_game(bot, game, "🎮 Выберите игру:", reply_markup=kb)

@common_router.callback_query(F.data == "select_bot")
async def cb_select_bot(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "selecting": 
        return await call.answer("Нельзя выбрать бота сейчас.", show_alert=True)
    
    game["players"].append({"user_id": bot.id, "name": "Бот 🤖", "timeouts": 0})
    await save_game(game)
    await show_game_menu(bot, chat_id, game)
    await call.answer("Бот присоединился! Выберите игру.")

@common_router.callback_query(F.data.startswith("select_"))
async def cb_select_game_type(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "selecting": 
        return await call.answer("Нельзя выбрать игру сейчас.", show_alert=True)
    
    if call.data == "select_bot": return
    
    game_type = call.data.split("_")[1]
    
    if game_type == "ttt" and len(game["players"]) > 2:
        return await call.answer("Для крестиков-ноликов нужно 1-2 игрока!", show_alert=True)
        
    if len(game["players"]) == 1:
        if not any(p["user_id"] == bot.id for p in game["players"]):
            game["players"].append({"user_id": bot.id, "name": "Бот 🤖", "timeouts": 0})
            
    game["game_type"] = game_type
    game["last_action_time"] = time.time()
    
    if game_type == "rps":
        from games.rps import start_rps
        game["state"] = "playing_rps"
        game["game_state"] = {"choices": {}}
        if any(p["user_id"] == bot.id for p in game["players"]):
            game["game_state"]["choices"][str(bot.id)] = random.choice(["rock", "paper", "scissors"])
        await start_rps(bot, chat_id, game)
        
    elif game_type == "ttt":
        from games.ttt import start_ttt
        game["state"] = "playing_ttt"
        players = game["players"]
        game["game_state"] = {
            "board": [0]*9,
            "turn": players[0]["user_id"],
            "symbols": {str(players[0]["user_id"]): "X"}
        }
        if len(players) > 1:
            game["game_state"]["symbols"][str(players[1]["user_id"])] = "O"
        await start_ttt(bot, chat_id, game)
        
    elif game_type == "dice":
        from games.dice import start_dice
        game["state"] = "playing_dice"
        game["game_state"] = {"rolls": {}}
        if any(p["user_id"] == bot.id for p in game["players"]):
            game["game_state"]["rolls"][str(bot.id)] = random.randint(1, 6)
        await start_dice(bot, chat_id, game)
        
    elif game_type == "slots":
        from games.slots import start_slots, generate_slot_roll
        game["state"] = "playing_slots"
        game["game_state"] = {"rolls": {}}
        if any(p["user_id"] == bot.id for p in game["players"]):
            game["game_state"]["rolls"][str(bot.id)] = generate_slot_roll()
        await start_slots(bot, chat_id, game)
        
    elif game_type == "diamond":
        from games.diamond import start_diamond
        game["state"] = "playing_diamond"
        players = game["players"]
        random.shuffle(players)
        game["game_state"] = {
            "board": [0]*9,
            "diamond_idx": random.randint(0, 8),
            "turn": players[0]["user_id"],
            "order": [p["user_id"] for p in players]
        }
        await start_diamond(bot, chat_id, game)
        
    elif game_type == "roulette":
        from games.roulette import start_roulette_betting
        game["state"] = "betting_roulette"
        game["game_state"] = {
            "bets": {str(p["user_id"]): 10 for p in game["players"]},
            "ready": []
        }
        await start_roulette_betting(bot, chat_id, game)
        
    elif game_type == "race":
        from games.race import start_race
        game["state"] = "playing_race"
        game["game_state"] = {"positions": {}, "ready": []}
        if any(p["user_id"] == bot.id for p in game["players"]):
            game["game_state"]["ready"].append(str(bot.id))
        await start_race(bot, chat_id, game)
        
    await call.answer()

@common_router.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(call: CallbackQuery, bot: Bot):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
    if game["state"] != "selecting":
        return await call.answer("Меню недоступно.", show_alert=True)
        
    if user_id not in [p["user_id"] for p in game["players"]]:
        return await call.answer("Вы не участник игры.", show_alert=True)
        
    await show_game_menu(bot, chat_id, game)
    await call.answer()

@common_router.callback_query(F.data == "skip_timeout_player")
async def cb_skip_timeout_player(call: CallbackQuery, bot: Bot):
    from bot import handle_timeout
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    game = await get_game(chat_id)
    if not game:
        try: await call.message.delete()
        except: pass
        return await call.answer("Эта игра была принудительно завершена администратором.", show_alert=True)
        
    if user_id not in [p["user_id"] for p in game["players"]]:
        return await call.answer("Вы не участвуете в этой игре!", show_alert=True)
        
    waiting_players = get_active_waiting_players(game)
    clicker_name = call.from_user.full_name
    if clicker_name in waiting_players:
        return await call.answer("Вы не можете пропустить собственный ход!", show_alert=True)
        
    await call.answer("Ход пропущен!")
    await handle_timeout(bot, chat_id, game)


