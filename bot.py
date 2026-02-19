import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8239867136:AAG32C-kC6HvDHQ2Z8rIVuufL9gCSIOiBrk"
ADMIN_ID = 8438380074
CHANNEL_ID = "-1003720906218"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

pending_posts = {}
moderation_mode = True

def get_moderation_keyboard(message_id: int):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"publish_{message_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{message_id}")
        ]
    ])
    return keyboard

def get_admin_panel():
    mode_text = "✅ Модерация (кнопки)" if moderation_mode else "📢 Прямой постинг"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔄 Режим: {mode_text}", callback_data="toggle_mode")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
    ])
    return keyboard

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "👋 Панель управления ботом\n\n"
            "Текущий режим: " + ("✅ Модерация (ты проверяешь посты)" if moderation_mode else "📢 Прямой постинг (посты сразу в канал)"),
            reply_markup=get_admin_panel()
        )
    else:
        await message.answer(
            "📝 Привет! Я бот для предложки.\n\n"
            "Отправь мне текст, фото или видео, которые хочешь предложить для канала."
        )

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Панель управления:", reply_markup=get_admin_panel())

@dp.callback_query(F.data == "toggle_mode")
async def toggle_mode(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Не для тебя!", show_alert=True)
        return
    
    global moderation_mode
    moderation_mode = not moderation_mode
    
    if moderation_mode:
        text = "✅ Включен режим модерации\nТеперь все сообщения будут приходить тебе с кнопками Да/Нет"
    else:
        text = "📢 Включен режим прямого постинга\nТеперь все сообщения будут сразу публиковаться в канал"
    
    await callback.message.edit_text(text, reply_markup=get_admin_panel())
    await callback.answer()

@dp.callback_query(F.data == "show_stats")
async def show_stats_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Не для тебя!", show_alert=True)
        return
    
    stats_text = (
        f"📊 Статистика:\n"
        f"• Режим: {'модерация' if moderation_mode else 'прямой постинг'}\n"
        f"• Ожидают модерации: {len(pending_posts)}\n"
        f"• ID канала: {CHANNEL_ID}"
    )
    
    await callback.message.edit_text(stats_text, reply_markup=get_admin_panel())
    await callback.answer()

@dp.callback_query(F.data == "help")
async def help_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Не для тебя!", show_alert=True)
        return
    
    help_text = (
        "ℹ️ Как это работает:\n\n"
        "🔹 Режим модерации - сообщения приходят тебе, ты решаешь публиковать или нет\n"
        "🔹 Режим прямого постинга - сообщения сразу уходят в канал\n\n"
        "Команды:\n"
        "/start - открыть панель\n"
        "/admin - открыть панель\n\n"
        "Кнопки в панели:\n"
        "• Режим - переключение между режимами\n"
        "• Статистика - просмотр текущего состояния\n"
        "• Помощь - это сообщение"
    )
    
    await callback.message.edit_text(help_text, reply_markup=get_admin_panel())
    await callback.answer()

@dp.message()
async def handle_user_message(message: types.Message):
    user = message.from_user
    
    if user.id == ADMIN_ID:
        return
    
    global moderation_mode
    
    if moderation_mode:
        await message.answer("⏳ Спасибо! Твое сообщение отправлено на модерацию.")
        
        try:
            sent_message = await message.copy_to(
                chat_id=ADMIN_ID,
                caption=f"📨 Новый пост от @{user.username or user.full_name} (ID: {user.id})\n\n{message.caption or ''}",
                reply_markup=get_moderation_keyboard(message.message_id)
            )
            
            pending_posts[sent_message.message_id] = {
                'user_id': user.id,
                'original_message': message
            }
            
        except Exception as e:
            logging.error(f"Ошибка при отправке админу: {e}")
            await message.answer("❌ Произошла ошибка. Попробуй позже.")
    
    else:
        try:
            await message.copy_to(chat_id=CHANNEL_ID)
            await message.answer("✅ Твое сообщение опубликовано в канале! Спасибо!")
        except Exception as e:
            logging.error(f"Ошибка публикации в канал: {e}")
            await message.answer("❌ Не удалось опубликовать сообщение. Попробуй позже.")
            await bot.send_message(
                ADMIN_ID,
                f"⚠️ Ошибка публикации в канал!\nСообщение от @{user.username or user.full_name} не удалось опубликовать."
            )

@dp.callback_query(F.data.startswith(('publish_', 'reject_')))
async def handle_moderation(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Это не для тебя!", show_alert=True)
        return
    
    action = callback.data.split('_')[0]
    post_data = pending_posts.get(callback.message.message_id)
    
    if not post_data:
        await callback.answer("❌ Пост уже обработан или устарел", show_alert=True)
        return
    
    await callback.message.edit_reply_markup(reply_markup=None)
    
    if action == 'publish':
        try:
            await post_data['original_message'].copy_to(chat_id=CHANNEL_ID)
            await callback.message.edit_text(f"{callback.message.text}\n\n✅ Пост опубликован в канале!")
            try:
                await bot.send_message(
                    chat_id=post_data['user_id'],
                    text="✅ Ура! Твой пост опубликован в канале. Спасибо!"
                )
            except:
                pass
            await callback.answer("✅ Опубликовано!")
        except Exception as e:
            logging.error(f"Ошибка публикации: {e}")
            await callback.message.edit_text(f"{callback.message.text}\n\n❌ Ошибка публикации: {e}")
            await callback.answer("❌ Ошибка!", show_alert=True)
    
    elif action == 'reject':
        await callback.message.edit_text(f"{callback.message.text}\n\n❌ Пост отклонен")
        try:
            await bot.send_message(
                chat_id=post_data['user_id'],
                text="😔 К сожалению, твой пост не прошел модерацию."
            )
        except:
            pass
        await callback.answer("❌ Отклонено")
    
    if callback.message.message_id in pending_posts:
        del pending_posts[callback.message.message_id]

async def main():
    print("🚀 Бот запущен!")
    print(f"Режим при запуске: {'Модерация' if moderation_mode else 'Прямой постинг'}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())