from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat

async def set_default_commands(bot: Bot):
    user_commands = [
        BotCommand(command="start", description="🏠 Главное меню / создать комнату"),
        BotCommand(command="profile", description="👤 Ваш профиль и баланс"),
        BotCommand(command="top", description="🏆 Топ игроков"),
        BotCommand(command="daily", description="🎁 Ежедневный бонус"),
        BotCommand(command="shop", description="🛒 Магазин"),
        BotCommand(command="inventory", description="🎒 Инвентарь"),
        BotCommand(command="arcade", description="🎰 Аркадный зал"),
        BotCommand(command="report", description="🚩 Отправить жалобу на игрока"),
        BotCommand(command="exit", description="🚪 Покинуть комнату/игру"),
        BotCommand(command="help", description="📖 Гайд и правила")
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

async def set_admin_commands(bot: Bot, admin_id: int):
    all_commands = [
        BotCommand(command="admin", description="🛠 Админ-панель (управление)"),
        BotCommand(command="rooms", description="📋 Список активных комнат"),
        BotCommand(command="start", description="🏠 Главное меню / создать комнату"),
        BotCommand(command="profile", description="👤 Ваш профиль и баланс"),
        BotCommand(command="top", description="🏆 Топ игроков"),
        BotCommand(command="daily", description="🎁 Ежедневный бонус"),
        BotCommand(command="shop", description="🛒 Магазин"),
        BotCommand(command="inventory", description="🎒 Инвентарь"),
        BotCommand(command="arcade", description="🎰 Аркадный зал"),
        BotCommand(command="report", description="🚩 Отправить жалобу на игрока"),
        BotCommand(command="exit", description="🚪 Покинуть комнату/игру"),
        BotCommand(command="maintenance", description="🛠 Вкл/Выкл тех. обслуживание"),
        BotCommand(command="help", description="📖 Гайд и правила")
    ]
    try:
        await bot.set_my_commands(all_commands, scope=BotCommandScopeChat(chat_id=admin_id))
    except Exception as e:
        import logging
        logging.error(f"Failed to set admin commands for {admin_id}: {e}")

async def remove_admin_commands(bot: Bot, admin_id: int):
    try:
        await bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=admin_id))
    except Exception:
        pass

async def setup_all_commands(bot: Bot):
    await set_default_commands(bot)
    from db import get_db
    async with get_db() as db:
        async with db.execute("SELECT user_id FROM admins") as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                await set_admin_commands(bot, row[0])
