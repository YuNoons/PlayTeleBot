import os
import json
import logging
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiogram import Bot
import aiosqlite
import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Переменные окружения и пути
DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bot", "game.db"))
CONFIG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bot", "config.json"))
config = {}
try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
except Exception:
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    logging.warning("Не указан токен бота (BOT_TOKEN)! Уведомления не будут работать.")
    BOT_TOKEN = "dummy_token"
# Инициализация FastAPI
app = FastAPI(
    title="TG Bot Admin Panel API",
    description="REST API для управления базой данных Telegram-бота из Tauri-панелей (PC и Android)",
    version="1.0.0"
)

# Разрешаем CORS, чтобы Tauri-приложение могло слать запросы
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хелпер для подключения к БД
async def get_db_connection():
    conn = await aiosqlite.connect(DB_FILE, timeout=20.0)
    await conn.execute('PRAGMA journal_mode=WAL;')
    try:
        yield conn
    finally:
        await conn.close()

# Инициализация Бота для отправки уведомлений (если указан токен)
bot = None
if BOT_TOKEN:
    try:
        bot = Bot(token=BOT_TOKEN)
    except Exception as e:
        print(f"Failed to initialize Bot: {e}")

# --- Схемы данных Pydantic ---

class UserUpdate(BaseModel):
    user_id: int
    name: str
    username: str
    coins: int
    title: str
    is_banned: int
    ban_reason: str
    ban_until: float

class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    price: int
    item_type: str
    value: str

class ItemUpdate(BaseModel):
    id: int
    name: str
    description: Optional[str] = ""
    price: int
    item_type: str
    value: str
    is_active: int

class ReportStatusUpdate(BaseModel):
    id: int
    status: str

class SettingsUpdate(BaseModel):
    settings: dict # {"maintenance_mode": "true", ...}

class BroadcastTaskCreate(BaseModel):
    message_text: str
    image_path: Optional[str] = None

class AdminCreate(BaseModel):
    user_id: int
    username: str
    level: int = 1

# --- Эндпоинты API ---

@app.get("/api/users")
async def get_users(query: Optional[str] = None, conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Получить список пользователей (с поиском по имени/юзернейму/ID)"""
    sql = "SELECT user_id, name, username, coins, title, games_played, wins, played_games, is_banned, ban_reason, ban_until, last_active, daily_earnings FROM users"
    params = []
    
    if query:
        sql += " WHERE name LIKE ? OR username LIKE ? OR CAST(user_id AS TEXT) LIKE ?"
        q_wildcard = f"%{query}%"
        params = [q_wildcard, q_wildcard, q_wildcard]
        
    async with conn.execute(sql, params) as cursor:
        rows = await cursor.fetchall()
        
    users = []
    for r in rows:
        played_games = {}
        if r[7]:
            try: played_games = json.loads(r[7])
            except: pass
            
        users.append({
            "user_id": r[0],
            "name": r[1],
            "username": r[2],
            "coins": r[3],
            "title": r[4],
            "games_played": r[5],
            "wins": r[6],
            "played_games": played_games,
            "is_banned": r[8],
            "ban_reason": r[9],
            "ban_until": r[10],
            "last_active": r[11],
            "daily_earnings": r[12]
        })
    return users

@app.post("/api/users/update")
async def update_user(user: UserUpdate, conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Обновить информацию о пользователе (включая бан/таймаут и баланс)"""
    try:
        await conn.execute('''
            UPDATE users 
            SET name = ?, username = ?, coins = ?, title = ?, is_banned = ?, ban_reason = ?, ban_until = ?
            WHERE user_id = ?
        ''', (user.name, user.username, user.coins, user.title, user.is_banned, user.ban_reason, user.ban_until, user.user_id))
        await conn.commit()
        return {"status": "success", "message": f"User {user.user_id} updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rooms")
async def get_rooms(conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Получить список активных игровых комнат"""
    async with conn.execute("SELECT chat_id, players, game_type, state FROM games") as cursor:
        rows = await cursor.fetchall()
        
    rooms = []
    for r in rows:
        players = []
        try: players = json.loads(r[1])
        except: pass
        
        rooms.append({
            "chat_id": r[0],
            "players": players,
            "game_type": r[2],
            "state": r[3]
        })
    return rooms

@app.delete("/api/rooms/{chat_id}")
async def delete_room(chat_id: int, conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Принудительно закрыть игровую комнату и уведомить чат"""
    # Сначала проверяем, есть ли комната
    async with conn.execute("SELECT chat_id FROM games WHERE chat_id = ?", (chat_id,)) as cursor:
        row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Room not found")
        
    # Удаляем из БД
    await conn.execute("DELETE FROM games WHERE chat_id = ?", (chat_id,))
    await conn.commit()
    
    # Отправляем сообщение в чат бота (если бот настроен)
    if bot:
        try:
            await bot.send_message(chat_id, "⚠️ <b>Эта игра была принудительно завершена администратором через панель управления.</b>", parse_mode="HTML")
        except Exception as e:
            logging.warning(f"Не удалось отправить уведомление о закрытии комнаты в чат {chat_id}: {e}")
    else:
        logging.info(f"Пропуск отправки сообщения в {chat_id}, так как BOT_TOKEN не задан")

        
    return {"status": "success", "message": f"Room {chat_id} closed."}

@app.get("/api/items")
async def get_items(conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Получить список товаров в магазине"""
    async with conn.execute("SELECT id, name, description, price, item_type, value, is_active FROM items") as cursor:
        rows = await cursor.fetchall()
    return [{
        "id": r[0],
        "name": r[1],
        "description": r[2],
        "price": r[3],
        "item_type": r[4],
        "value": r[5],
        "is_active": r[6]
    } for r in rows]

@app.post("/api/items")
async def create_item(item: ItemCreate, conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Создать новый товар в магазине"""
    try:
        await conn.execute('''
            INSERT INTO items (name, description, price, item_type, value, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (item.name, item.description, item.price, item.item_type, item.value))
        await conn.commit()
        return {"status": "success", "message": "Item created."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/items/update")
async def update_item(item: ItemUpdate, conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Обновить товар в магазине (или архивировать/активировать)"""
    try:
        await conn.execute('''
            UPDATE items 
            SET name = ?, description = ?, price = ?, item_type = ?, value = ?, is_active = ?
            WHERE id = ?
        ''', (item.name, item.description, item.price, item.item_type, item.value, item.is_active, item.id))
        await conn.commit()
        return {"status": "success", "message": "Item updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/items/{item_id}")
async def delete_item(item_id: int, conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Удалить товар из магазина"""
    try:
        await conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        await conn.commit()
        return {"status": "success", "message": f"Item {item_id} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports")
async def get_reports(conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Получить список жалоб"""
    async with conn.execute("SELECT id, sender_id, sender_name, target_id, reason, status, created_at FROM reports ORDER BY created_at DESC") as cursor:
        rows = await cursor.fetchall()
    return [{
        "id": r[0],
        "sender_id": r[1],
        "sender_name": r[2],
        "target_id": r[3],
        "reason": r[4],
        "status": r[5],
        "created_at": r[6]
    } for r in rows]

@app.post("/api/reports/status")
async def update_report_status(report: ReportStatusUpdate, conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Обновить статус жалобы (например, 'resolved', 'ignored')"""
    try:
        await conn.execute("UPDATE reports SET status = ? WHERE id = ?", (report.status, report.id))
        await conn.commit()
        return {"status": "success", "message": "Report status updated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings")
async def get_settings(conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Получить глобальные настройки бота"""
    async with conn.execute("SELECT key, value FROM bot_settings") as cursor:
        rows = await cursor.fetchall()
    return {r[0]: r[1] for r in rows}

@app.post("/api/settings")
async def save_settings(settings_data: SettingsUpdate, conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Сохранить глобальные настройки бота"""
    try:
        for key, value in settings_data.settings.items():
            await conn.execute('''
                INSERT OR REPLACE INTO bot_settings (key, value)
                VALUES (?, ?)
            ''', (key, str(value)))
        await conn.commit()
        return {"status": "success", "message": "Settings saved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/broadcast")
async def add_broadcast_task(task: BroadcastTaskCreate, conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Добавить сообщение в очередь рассылки"""
    try:
        await conn.execute('''
            INSERT INTO broadcast_tasks (message_text, image_path, status)
            VALUES (?, ?, 'pending')
        ''', (task.message_text, task.image_path))
        await conn.commit()
        return {"status": "success", "message": "Broadcast task queued."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admins")
async def get_admins(conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Получить список администраторов"""
    async with conn.execute("SELECT user_id, username, level, added_by, added_at FROM admins") as cursor:
        rows = await cursor.fetchall()
    return [{
        "user_id": r[0],
        "username": r[1],
        "level": r[2],
        "added_by": r[3],
        "added_at": r[4]
    } for r in rows]

@app.get("/api/admin_logs")
async def get_admin_logs(conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Получить историю действий администраторов"""
    async with conn.execute("SELECT id, admin_id, admin_name, action, target_user, target_chat, details, timestamp FROM admin_logs ORDER BY timestamp DESC LIMIT 100") as cursor:
        rows = await cursor.fetchall()
    return [{
        "id": r[0],
        "admin_id": r[1],
        "admin_name": r[2],
        "action": r[3],
        "target_user": r[4],
        "target_chat": r[5],
        "details": r[6],
        "timestamp": r[7]
    } for r in rows]

@app.post("/api/admins")
async def add_admin(admin: AdminCreate, conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Добавить нового администратора"""
    try:
        await conn.execute('''
            INSERT OR REPLACE INTO admins (user_id, username, level)
            VALUES (?, ?, ?)
        ''', (admin.user_id, admin.username, admin.level))
        await conn.commit()
        return {"status": "success", "message": f"Admin {admin.user_id} added."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admins/{user_id}")
async def delete_admin(user_id: int, conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Удалить администратора"""
    try:
        await conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        await conn.commit()
        return {"status": "success", "message": f"Admin {user_id} deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard_stats")
async def get_dashboard_stats(conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Получить общую статистику для дашборда"""
    try:
        async with conn.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0]
            
        async with conn.execute("SELECT COUNT(*) FROM games") as cursor:
            active_rooms = (await cursor.fetchone())[0]
            
        async with conn.execute("SELECT COALESCE(SUM(coins), 0) FROM users") as cursor:
            total_coins = (await cursor.fetchone())[0]
            
        return {
            "total_users": total_users,
            "active_rooms": active_rooms,
            "total_coins": total_coins
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics")
async def get_metrics(conn: aiosqlite.Connection = Depends(get_db_connection)):
    """Получить историю метрик для графиков"""
    async with conn.execute("SELECT timestamp, total_users, total_coins, active_games FROM metrics_history ORDER BY timestamp ASC LIMIT 50") as cursor:
        rows = await cursor.fetchall()
    return [{
        "timestamp": r[0],
        "total_users": r[1],
        "total_coins": r[2],
        "active_games": r[3]
    } for r in rows]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
