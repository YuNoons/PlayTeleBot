import re

with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add delete_after and edit_or_send
replacement_1 = """# --- Удаление сообщений ---
async def delete_last_message(bot: Bot, chat_id: int, message_id: int):
    \"\"\"Удаляет предыдущее игровое сообщение для очистки чата\"\"\"
    if message_id:
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception as e:
            pass # Игнорируем ошибки (например сообщение уже удалено)

async def delete_after(bot: Bot, chat_id: int, message_id: int, delay: int):
    \"\"\"Удаляет сообщение через заданное время (в секундах)\"\"\"
    if delay > 0:
        await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

async def edit_or_send(bot: Bot, chat_id: int, message_id: int, text: str, reply_markup=None, parse_mode=None):
    \"\"\"Пытается отредактировать сообщение. Если не вышло — шлет новое.\"\"\"
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
    return msg.message_id"""

content = re.sub(r'# --- Удаление сообщений ---.*?(?=# --- 0\. Экономика)', replacement_1, content, flags=re.DOTALL)

# Add bot: Bot to various commands
content = content.replace('async def cmd_help(message: Message):', 'async def cmd_help(message: Message, bot: Bot):')
content = content.replace('async def cmd_profile(message: Message):', 'async def cmd_profile(message: Message, bot: Bot):')
content = content.replace('async def cmd_top(message: Message):', 'async def cmd_top(message: Message, bot: Bot):')
content = content.replace('async def cmd_daily(message: Message):', 'async def cmd_daily(message: Message, bot: Bot):')
content = content.replace('async def cmd_shop(message: Message):', 'async def cmd_shop(message: Message, bot: Bot):')
content = content.replace('async def cmd_buy(message: Message):', 'async def cmd_buy(message: Message, bot: Bot):')

# In all cmd_, add asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))
# and change await message.answer(...) to msg = await ... \n asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 10))

def patch_answer(match):
    prefix = match.group(1)
    ans = match.group(2)
    return f"msg = {ans}\n{prefix}asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))"

content = re.sub(r'(\s+)await message\.answer\((.*?)\)', patch_answer, content)
content = re.sub(r'(\s+)return await message\.answer\((.*?)\)', r'\1msg = await message.answer(\2)\1asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))\1return', content)

def patch_cmd_start(match):
    return match.group(0) + '\n    asyncio.create_task(delete_after(bot, message.chat.id, message.message_id, 0))'

content = re.sub(r'async def cmd_[a-z_]+\(message: Message, bot: Bot\):', patch_cmd_start, content)
content = re.sub(r'async def cmd_exit\(message: Message, bot: Bot\):', patch_cmd_start, content)

# Now Stage 1 cmd_start logic completely replaced
cmd_start_repl = '''@dp.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    """Команда /start — создаёт игровую комнату или подключает игрока"""
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
        
    players = [{"user_id": message.from_user.id, "name": message.from_user.full_name, "timeouts": 0}]
    
    game = {
        "chat_id": chat_id,
        "players": players,
        "game_type": "",
        "game_state": {},
        "last_message_id": 0,
        "last_action_time": time.time(),
        "state": "waiting"
    }
    
    bot_info = await bot.get_me()
    invite_url = f"https://t.me/{bot_info.username}?start=invite"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Присоединиться", callback_data="join_game"),
            InlineKeyboardButton(text="🎮 Начать игру", callback_data="start_game")
        ],
        [
            InlineKeyboardButton(text="👥 Пригласить коллег", url=invite_url),
            InlineKeyboardButton(text="📊 Рейтинг компании", callback_data="show_top")
        ]
    ])
    
    game["last_message_id"] = await edit_or_send(
        bot, chat_id, 0, 
        f"🏢 Добро пожаловать в Корпоратив!\\n{message.from_user.full_name} присоединился. Сейчас в комнате: 1/3", 
        kb
    )
    await save_game(game)'''

content = re.sub(r'@dp\.message\(CommandStart\(\)\).*?async def cmd_start\(message: Message, bot: Bot\):.*?await save_game\(game\)', cmd_start_repl, content, flags=re.DOTALL)

# Add show_top handler
show_top_handler = '''@dp.callback_query(F.data == "show_top")
async def cb_show_top(call: CallbackQuery, bot: Bot):
    async with get_db() as db:
        async with db.execute("SELECT name, title, wins, coins FROM users ORDER BY coins DESC, wins DESC LIMIT 3") as cursor:
            rows = await cursor.fetchall()
            
    if not rows:
        return await call.answer("Рейтинг пока пуст.", show_alert=True)
        
    text = "🏆 <b>Топ 3 компании:</b>\\n\\n"
    for i, (name, title, wins, coins) in enumerate(rows):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else "🏅"
        text += f"{medal} <b>{name}</b> [{title}] — {coins} 🪙 ({wins} побед)\\n"
        
    msg = await bot.send_message(call.message.chat.id, text, parse_mode="HTML")
    asyncio.create_task(delete_after(bot, msg.chat.id, msg.message_id, 15))
    await call.answer()
'''

content = content.replace('# --- 1. Управление игроками ---', '# --- 1. Управление игроками ---\n\n' + show_top_handler)

# Patch cb_join_game
cb_join_game_repl = '''@dp.callback_query(F.data == "join_game")
async def cb_join_game(call: CallbackQuery, bot: Bot):
    """Обработчик кнопки 'Присоединиться'"""
    chat_id = call.message.chat.id
    game = await get_game(chat_id)
    if not game or game["state"] != "waiting":
        return await call.answer("Игра недоступна или уже началась.", show_alert=True)
        
    user_id = call.from_user.id
    
    if any(p["user_id"] == user_id for p in game["players"]):
        return await call.answer("Вы уже в игре!", show_alert=True)
        
    if len(game["players"]) >= 3:
        return await call.answer("Достигнуто максимальное количество игроков (3).", show_alert=True)
        
    game["players"].append({"user_id": user_id, "name": call.from_user.full_name, "timeouts": 0})
    game["last_action_time"] = time.time()
    
    bot_info = await bot.get_me()
    invite_url = f"https://t.me/{bot_info.username}?start=invite"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Присоединиться", callback_data="join_game"),
            InlineKeyboardButton(text="🎮 Начать игру", callback_data="start_game")
        ],
        [
            InlineKeyboardButton(text="👥 Пригласить коллег", url=invite_url),
            InlineKeyboardButton(text="📊 Рейтинг компании", callback_data="show_top")
        ]
    ])
    
    players_text = "\\n".join([f"{i+1}. {p['name']}" for i, p in enumerate(game["players"])])
    text = f"🏢 Добро пожаловать в Корпоратив!\\nИгроки ({len(game['players'])}/3):\\n{players_text}"
    
    game["last_message_id"] = await edit_or_send(bot, chat_id, game["last_message_id"], text, kb)
    await save_game(game)
    await call.answer("Вы присоединились!")'''

content = re.sub(r'@dp\.callback_query\(F\.data == "join_game"\).*?await call\.answer\("Вы присоединились!"\)', cb_join_game_repl, content, flags=re.DOTALL)

# Refactor all edit_or_send patterns instead of delete + send
content = re.sub(
    r'await delete_last_message\(bot, chat_id, game\["last_message_id"\]\)\s+msg = await bot\.send_message\(chat_id, (.*?), reply_markup=(.*?), parse_mode=(.*?)\)\s+game\["last_message_id"\] = msg\.message_id',
    r'game["last_message_id"] = await edit_or_send(bot, chat_id, game["last_message_id"], \1, reply_markup=\2, parse_mode=\3)',
    content
)
content = re.sub(
    r'await delete_last_message\(bot, chat_id, game\["last_message_id"\]\)\s+msg = await bot\.send_message\(chat_id, (.*?), reply_markup=(.*?)\)\s+game\["last_message_id"\] = msg\.message_id',
    r'game["last_message_id"] = await edit_or_send(bot, chat_id, game["last_message_id"], \1, reply_markup=\2)',
    content
)
content = re.sub(
    r'await delete_last_message\(bot, chat_id, game\["last_message_id"\]\)\s+msg = await bot\.send_message\(chat_id, (.*?)\)\s+game\["last_message_id"\] = msg\.message_id',
    r'game["last_message_id"] = await edit_or_send(bot, chat_id, game["last_message_id"], \1)',
    content
)

# And those without assignment to last_message_id, typically game over
content = re.sub(
    r'await delete_last_message\(bot, chat_id, game\["last_message_id"\]\)\s+await bot\.send_message\(chat_id, (.*?), reply_markup=(.*?), parse_mode=(.*?)\)',
    r'await edit_or_send(bot, chat_id, game["last_message_id"], \1, reply_markup=\2, parse_mode=\3)',
    content
)
content = re.sub(
    r'await delete_last_message\(bot, chat_id, game\["last_message_id"\]\)\s+await bot\.send_message\(chat_id, (.*?), reply_markup=(.*?)\)',
    r'await edit_or_send(bot, chat_id, game["last_message_id"], \1, reply_markup=\2)',
    content
)
content = re.sub(
    r'await delete_last_message\(bot, chat_id, game\["last_message_id"\]\)\s+await bot\.send_message\(chat_id, (.*?)\)',
    r'await edit_or_send(bot, chat_id, game["last_message_id"], \1)',
    content
)

# Replace try-except edit_text with edit_or_send
try_except_pattern = r'''        try:
            await call\.message\.edit_text\(
                (.*?), 
                reply_markup=(.*?)
            \)
        except:
            pass'''
content = re.sub(try_except_pattern, r'        game["last_message_id"] = await edit_or_send(bot, chat_id, game["last_message_id"], \1, reply_markup=\2)', content)

# And try-except in join_game, if any left
try_except_pattern2 = r'''    try:
        await call\.message\.edit_text\((.*?), reply_markup=(.*?)\)
    except Exception:
        pass'''
content = re.sub(try_except_pattern2, r'    game["last_message_id"] = await edit_or_send(bot, chat_id, game["last_message_id"], \1, reply_markup=\2)', content)


# write back
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)
