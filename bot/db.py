import aiosqlite
import json
import logging
from typing import Optional

DB_FILE = "game.db"
db_ready = False

def get_db():
    """Возвращает подключение к БД с увеличенным таймаутом для защиты от блокировок"""
    return aiosqlite.connect(DB_FILE, timeout=20.0)

async def init_db(bot):
    """Инициализация базы данных и очистка старых игр"""
    global db_ready
    logging.info("Инициализация базы данных и очистка старых сообщений...")
    async with get_db() as db:
        await db.execute('PRAGMA journal_mode=WAL;')
        # Создаем таблицу пользователей для статистики, если ее нет
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                games_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                game_type TEXT,
                players TEXT,
                winners TEXT,
                timestamp REAL
            )
        ''')
        
        # Обновление схемы (добавление колонок)
        for col, col_def in [
            ("coins", "INTEGER DEFAULT 100"), 
            ("title", "TEXT DEFAULT 'Новичок'"), 
            ("last_daily", "REAL DEFAULT 0"),
            ("played_games", "TEXT DEFAULT '{}'"),
            ("username", "TEXT DEFAULT ''"),
            ("last_chat_id", "INTEGER DEFAULT 0"),
            ("is_banned", "INTEGER DEFAULT 0"),
            ("ban_reason", "TEXT DEFAULT ''"),
            ("ban_until", "REAL DEFAULT 0"),
            ("last_active", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("daily_earnings", "INTEGER DEFAULT 0"),
            ("daily_earnings_date", "TEXT DEFAULT ''")
        ]:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {col_def}")
            except Exception:
                pass # Колонка уже существует
        
        # Очистка старых сообщений
        try:
            async with db.execute("SELECT chat_id, last_message_id FROM games") as cursor:
                rows = await cursor.fetchall()
            for chat_id, msg_id in rows:
                if msg_id:
                    try:
                        await bot.delete_message(chat_id, msg_id)
                    except Exception:
                        pass
        except Exception:
            pass
            
        # Таблицы для админ-панели
        await db.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                level INTEGER DEFAULT 1,
                added_by INTEGER,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                admin_name TEXT,
                action TEXT,
                target_user TEXT,
                target_chat INTEGER,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        import os
        import json
        config = {}
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass

        owner_id = os.getenv("OWNER_ID") or config.get("owner_id")
        if not owner_id:
            try:
                with open("OWNER_ID.env", "r") as f:
                    owner_id = f.read().strip()
            except Exception:
                pass
                
        if owner_id and str(owner_id).isdigit():
            await db.execute("INSERT OR IGNORE INTO admins (user_id, username, level) VALUES (?, 'Owner', 2)", (int(owner_id),))
            await db.execute("UPDATE admins SET level = 2 WHERE user_id = ?", (int(owner_id),))

        # Назначаем остальных админов из конфига
        admins = config.get("admins", [])
        for admin_id in admins:
            if str(admin_id).isdigit():
                await db.execute("INSERT OR IGNORE INTO admins (user_id, username, level) VALUES (?, 'Admin', 1)", (int(admin_id),))
                
        junior_admins = config.get("junior_admins", [])
        for admin_id in junior_admins:
            if str(admin_id).isdigit():
                await db.execute("INSERT OR IGNORE INTO admins (user_id, username, level) VALUES (?, 'Junior Admin', 1)", (int(admin_id),))
            
        await db.execute("DROP TABLE IF EXISTS games")
        await db.execute('''
            CREATE TABLE games (
                chat_id INTEGER PRIMARY KEY,
                players TEXT,
                game_type TEXT,
                game_state TEXT,
                last_message_id INTEGER,
                last_action_time REAL,
                state TEXT,
                last_text TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                value TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(item_id) REFERENCES items(id)
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_users INTEGER DEFAULT 0,
                total_coins INTEGER DEFAULT 0,
                active_games INTEGER DEFAULT 0
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                sender_name TEXT,
                target_id INTEGER,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS broadcast_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_text TEXT NOT NULL,
                image_path TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        await db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('maintenance_mode', 'false')")
        await db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('welcome_bonus_amount', '100')")
        await db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('max_games_per_user', '5')")
        await db.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('max_daily_earnings', '500')")
        
        await db.commit()
    db_ready = True
    logging.info("База данных готова.")

async def get_game(chat_id: int) -> Optional[dict]:
    """Получение текущей игры по chat_id"""
    async with get_db() as db:
        async with db.execute("SELECT chat_id, players, game_type, game_state, last_message_id, last_action_time, state, last_text FROM games WHERE chat_id=?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "chat_id": row[0],
                    "players": json.loads(row[1]),
                    "game_type": row[2],
                    "game_state": json.loads(row[3]),
                    "last_message_id": row[4],
                    "last_action_time": row[5],
                    "state": row[6],
                    "last_text": row[7] or ""
                }
    return None

async def save_game(game: dict):
    """Сохранение или обновление состояния игры"""
    async with get_db() as db:
        await db.execute('''
            INSERT OR REPLACE INTO games 
            (chat_id, players, game_type, game_state, last_message_id, last_action_time, state, last_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            game["chat_id"],
            json.dumps(game["players"]),
            game["game_type"],
            json.dumps(game["game_state"]),
            game["last_message_id"],
            game["last_action_time"],
            game["state"],
            game.get("last_text", "")
        ))
        await db.commit()

async def delete_game(chat_id: int):
    """Удаление игры из базы данных"""
    async with get_db() as db:
        await db.execute("DELETE FROM games WHERE chat_id=?", (chat_id,))
        await db.commit()

async def update_stats(bot_id: int, players: list, winners: list, coins_override: Optional[dict] = None, game_type: str = "", chat_id: int = 0):
    """Обновляет статистику игроков в БД, начисляет монеты и обновляет историю сыгранных игр"""
    async with get_db() as db:
        for p in players:
            if p["user_id"] == bot_id: continue
            
            # username может не быть в p, так как мы его не везде передавали, поэтому используем get
            username = p.get("username", "")
            
            cursor = await db.execute("INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)", (p["user_id"], p["name"]))
            if cursor.rowcount > 0:
                bonus = await get_setting("welcome_bonus_amount", "100")
                try:
                    bonus_val = int(bonus)
                except:
                    bonus_val = 100
                await db.execute("UPDATE users SET coins = ? WHERE user_id = ?", (bonus_val, p["user_id"]))
                
            await db.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, p["user_id"]))
            if chat_id != 0:
                await db.execute("UPDATE users SET last_chat_id = ? WHERE user_id = ?", (chat_id, p["user_id"]))
            
            async with db.execute("SELECT played_games FROM users WHERE user_id = ?", (p["user_id"],)) as cursor:
                row = await cursor.fetchone()
                
            played_games_dict = {}
            if row and row[0]:
                try:
                    played_games_dict = json.loads(row[0])
                except Exception:
                    played_games_dict = {}
                    
            if game_type:
                played_games_dict[game_type] = played_games_dict.get(game_type, 0) + 1
                
            played_games_json = json.dumps(played_games_dict)
            
            is_winner = p["name"] in winners
            if coins_override and p["user_id"] in coins_override:
                coins_earned = coins_override[p["user_id"]]
            else:
                coins_earned = 20 if is_winner else -5
                if len(winners) == 0: coins_earned = 5
            
            # Проверка лимита заработка за день
            import datetime
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            
            async with db.execute("SELECT daily_earnings_date, daily_earnings FROM users WHERE user_id = ?", (p["user_id"],)) as cursor:
                row = await cursor.fetchone()
                
            daily_date = row[0] if row else ""
            daily_earnings = row[1] if row else 0
            
            if daily_date != current_date:
                daily_earnings = 0
                await db.execute("UPDATE users SET daily_earnings_date = ?, daily_earnings = 0 WHERE user_id = ?", (current_date, p["user_id"]))
            
            # Применяем лимит только если зарабатываем монеты
            max_daily = int(await get_setting("max_daily_earnings", "200"))
            new_daily = daily_earnings
            
            if coins_earned > 0:
                available_to_earn = max_daily - daily_earnings
                if available_to_earn <= 0:
                    coins_earned = 0
                elif coins_earned > available_to_earn:
                    coins_earned = available_to_earn
                
                new_daily = daily_earnings + coins_earned
            
            await db.execute(
                "UPDATE users SET games_played = IFNULL(games_played, 0) + 1, wins = IFNULL(wins, 0) + ?, coins = MAX(0, IFNULL(coins, 0) + ?), played_games = ?, daily_earnings = ? WHERE user_id = ?",
                (1 if is_winner else 0, coins_earned, played_games_json, new_daily, p["user_id"])
            )
        await db.commit()

async def add_history(chat_id: int, game_type: str, players: list, winners: list):
    """Добавляет запись об игре в историю чата"""
    import time
    async with get_db() as db:
        await db.execute('''
            INSERT INTO history (chat_id, game_type, players, winners, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (chat_id, game_type, json.dumps(players), json.dumps(winners), time.time()))
        await db.commit()

async def get_history(chat_id: int, limit: int = 5) -> list:
    """Возвращает историю игр для чата"""
    async with get_db() as db:
        async with db.execute("SELECT game_type, players, winners, timestamp FROM history WHERE chat_id=? ORDER BY timestamp DESC LIMIT ?", (chat_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [{"game_type": r[0], "players": json.loads(r[1]), "winners": json.loads(r[2]), "timestamp": r[3]} for r in rows]

async def get_admin_level(user_id: int) -> int:
    """Возвращает уровень админа (0 если не админ)"""
    async with get_db() as db:
        async with db.execute("SELECT level FROM admins WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def log_admin_action(admin_id: int, admin_name: str, action: str, target_user: str = "", target_chat: int = 0, details: str = ""):
    """Логирует действие админа"""
    async with get_db() as db:
        await db.execute('''
            INSERT INTO admin_logs (admin_id, admin_name, action, target_user, target_chat, details)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (admin_id, admin_name, action, target_user, target_chat, details))
        await db.commit()

async def update_user_info(user_id: int, name: str, username: str, chat_id: int):
    """Обновляет базовую инфу юзера при любом действии, сохраняет последний чат-группу для уведомлений"""
    async with get_db() as db:
        cursor = await db.execute("INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)", (user_id, name))
        if cursor.rowcount > 0:
            bonus = await get_setting("welcome_bonus_amount", "100")
            try:
                bonus_val = int(bonus)
            except:
                bonus_val = 100
            await db.execute("UPDATE users SET coins = ? WHERE user_id = ?", (bonus_val, user_id))
            
        if chat_id != 0:
            await db.execute("UPDATE users SET name = ?, username = ?, last_chat_id = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?", (name, username, chat_id, user_id))
        else:
            await db.execute("UPDATE users SET name = ?, username = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?", (name, username, user_id))
        await db.commit()

async def get_active_items() -> list:
    """Возвращает список активных товаров в магазине"""
    async with get_db() as db:
        async with db.execute("SELECT id, name, description, price, item_type FROM items WHERE is_active = 1") as cursor:
            rows = await cursor.fetchall()
            return [{"id": r[0], "name": r[1], "description": r[2], "price": r[3], "item_type": r[4]} for r in rows]

async def buy_item(user_id: int, item_id: int) -> tuple[bool, str]:
    """Транзакция покупки товара. Возвращает (успех, сообщение)"""
    async with get_db() as db:
        try:
            await db.execute("BEGIN TRANSACTION;")
            
            # Проверяем баланс
            async with db.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    await db.execute("ROLLBACK;")
                    return False, "Пользователь не найден."
                coins = row[0]
            
            # Проверяем цену и товар
            async with db.execute("SELECT price, item_type, value FROM items WHERE id = ?", (item_id,)) as cursor:
                item_row = await cursor.fetchone()
                if not item_row:
                    await db.execute("ROLLBACK;")
                    return False, "Товар не найден."
                price, item_type, value = item_row
                
            if coins < price:
                await db.execute("ROLLBACK;")
                return False, "Недостаточно монет."
                
            # Списываем монеты
            await db.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (price, user_id))
            
            # Добавляем товар в инвентарь
            await db.execute("INSERT INTO user_items (user_id, item_id) VALUES (?, ?)", (user_id, item_id))
            
            # Если это титул, сразу применяем
            if item_type == "title":
                await db.execute("UPDATE users SET title = ? WHERE user_id = ?", (value, user_id))
                
            await db.execute("COMMIT;")
            return True, "Успешная покупка!"
        except Exception as e:
            await db.execute("ROLLBACK;")
            logging.error(f"Ошибка при покупке: {e}")
            return False, "Произошла ошибка при покупке."

async def get_user_inventory(user_id: int) -> list:
    """Возвращает купленные товары юзера"""
    async with get_db() as db:
        query = '''
            SELECT i.name, i.item_type, i.value, ui.purchased_at 
            FROM user_items ui 
            JOIN items i ON ui.item_id = i.id 
            WHERE ui.user_id = ?
        '''
        async with db.execute(query, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{"name": r[0], "item_type": r[1], "value": r[2], "purchased_at": r[3]} for r in rows]

async def capture_metrics():
    """Сохраняет текущие метрики системы (пользователи, монеты, игры) в историю"""
    async with get_db() as db:
        try:
            # Считаем пользователей
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                row = await cursor.fetchone()
                total_users = row[0] if row else 0
                
            # Считаем монеты
            async with db.execute("SELECT SUM(coins) FROM users") as cursor:
                row = await cursor.fetchone()
                total_coins = row[0] if row and row[0] else 0
                
            # Считаем игры
            async with db.execute("SELECT COUNT(*) FROM games") as cursor:
                row = await cursor.fetchone()
                active_games = row[0] if row else 0
                
            # Записываем в метрики
            await db.execute(
                "INSERT INTO metrics_history (total_users, total_coins, active_games) VALUES (?, ?, ?)",
                (total_users, total_coins, active_games)
            )
            await db.commit()
            logging.debug(f"Metrics captured: Users={total_users}, Coins={total_coins}, Games={active_games}")
        except Exception as e:
            logging.error(f"Error capturing metrics: {e}")

async def create_report(sender_id: int, sender_name: str, target_id: int, reason: str):
    """Создает новую жалобу в базе данных"""
    async with get_db() as db:
        await db.execute('''
            INSERT INTO reports (sender_id, sender_name, target_id, reason)
            VALUES (?, ?, ?, ?)
        ''', (sender_id, sender_name, target_id, reason))
        await db.commit()

# --- Настройки ---
settings_cache = {}
last_settings_update = 0

async def get_all_settings() -> dict:
    global settings_cache, last_settings_update
    import time
    if time.time() - last_settings_update > 60 or not settings_cache:
        async with get_db() as db:
            async with db.execute("SELECT key, value FROM bot_settings") as cursor:
                rows = await cursor.fetchall()
                settings_cache = {r[0]: r[1] for r in rows}
        last_settings_update = time.time()
    return settings_cache

async def get_setting(key: str, default: str = "") -> str:
    settings = await get_all_settings()
    return settings.get(key, default)


