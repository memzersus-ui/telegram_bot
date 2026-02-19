import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

BOT_TOKEN = "8239867136:AAG32C-kC6HvDHQ2Z8rIVuufL9gCSIOiBrk"
ADMIN_ID = 8438380074
CHANNEL_ID = "-1003720906218"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

pending_posts = {}
moderation_mode = True

def get_moderation_keyboard(message_id: int):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Опубликовать", callback_data=f"publish_{message_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{message_id}")
    )
    return keyboard

def get_admin_panel():
    mode_text = "✅ Модерация (кнопки)" if moderation_mode else "📢 Прямой постинг"
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"🔄 Режим: {mode_text}", callback_data="toggle_mode"))
    keyboard.add(InlineKeyboardButton("📊 Статистика", callback_data="show_stats"))
    keyboard.add(InlineKeyboardButton("ℹ️ Помощь", callback_data="help"))
    return keyboard

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply(
            "👋 Панель управления ботом\n\n"
            "Текущий режим: " + ("✅ Модерация (ты проверяешь посты)" if moderation_mode else "📢 Прямой постинг (посты сразу в канал)"),
            reply_markup=get_admin_panel()
        )
    else:
        await message.reply(
            "📝 Привет! Я бот для предложки.\n\n"
            "Отправь мне текст, фото или видео, которые хочешь предложить для канала."
        )

@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.reply("Панель управления:", reply_markup=get_admin_panel())

@dp.callback_query_handler(lambda c: c.data == 'toggle_mode')
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
    
    await bot.edit_message_text(text, chat_id=callback.message.chat.id, message_id=callback.message.message_id, reply_markup=get_admin_panel())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'show_stats')
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
    
    await bot.edit_message_text(stats_text, chat_id=callback.message.chat.id, message_id=callback.message.message_id, reply_markup=get_admin_panel())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == 'help')
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
    
    await bot.edit_message_text(help_text, chat_id=callback.message.chat.id, message_id=callback.message.message_id, reply_markup=get_admin_panel())
    await callback.answer()

@dp.message_handler(content_types=['text', 'photo', 'video', 'document', 'audio'])
async def handle_user_message(message: types.Message):
    user = message.from_user
    
    if user.id == ADMIN_ID:
        return
    
    global moderation_mode
    
    if moderation_mode:
        await message.reply("⏳ Спасибо! Твое сообщение отправлено на модерацию.")
        
        try:
            if message.photo:
                caption = f"📨 Новый пост от @{user.username or user.full_name} (ID: {user.id})\n\n{message.caption or ''}"
                sent_message = await bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=message.photo[-1].file_id,
                    caption=caption,
                    reply_markup=get_moderation_keyboard(message.message_id)
                )
            elif message.video:
                caption = f"📨 Новый пост от @{user.username or user.full_name} (ID: {user.id})\n\n{message.caption or ''}"
                sent_message = await bot.send_video(
                    chat_id=ADMIN_ID,
                    video=message.video.file_id,
                    caption=caption,
                    reply_markup=get_moderation_keyboard(message.message_id)
                )
            elif message.document:
                caption = f"📨 Новый пост от @{user.username or user.full_name} (ID: {user.id})\n\n{message.caption or ''}"
                sent_message = await bot.send_document(
                    chat_id=ADMIN_ID,
                    document=message.document.file_id,
                    caption=caption,
                    reply_markup=get_moderation_keyboard(message.message_id)
                )
            else:
                sent_message = await bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"📨 Новый пост от @{user.username or user.full_name} (ID: {user.id})\n\n{message.text}",
                    reply_markup=get_moderation_keyboard(message.message_id)
                )
            
            pending_posts[sent_message.message_id] = {
                'user_id': user.id,
                'original_message': message
            }
            
        except Exception as e:
            logging.error(f"Ошибка при отправке админу: {e}")
            await message.reply("❌ Произошла ошибка. Попробуй позже.")
    
    else:
        try:
            if message.photo:
                await bot.send_photo(CHANNEL_ID, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                await bot.send_video(CHANNEL_ID, message.video.file_id, caption=message.caption)
            elif message.document:
                await bot.send_document(CHANNEL_ID, message.document.file_id, caption=message.caption)
            else:
                await bot.send_message(CHANNEL_ID, message.text)
            
            await message.reply("✅ Твое сообщение опубликовано в канале! Спасибо!")
        except Exception as e:
            logging.error(f"Ошибка публикации в канал: {e}")
            await message.reply("❌ Не удалось опубликовать сообщение. Попробуй позже.")
            await bot.send_message(
                ADMIN_ID,
                f"⚠️ Ошибка публикации в канал!\nСообщение от @{user.username or user.full_name} не удалось опубликовать."
            )

@dp.callback_query_handler(lambda c: c.data.startswith('publish_') or c.data.startswith('reject_'))
async def handle_moderation(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Это не для тебя!", show_alert=True)
        return
    
    action = callback.data.split('_')[0]
    post_data = pending_posts.get(callback.message.message_id)
    
    if not post_data:
        await callback.answer("❌ Пост уже обработан или устарел", show_alert=True)
        return
    
    if action == 'publish':
        try:
            original_msg = post_data['original_message']
            
            if original_msg.photo:
                await bot.send_photo(CHANNEL_ID, original_msg.photo[-1].file_id, caption=original_msg.caption)
            elif original_msg.video:
                await bot.send_video(CHANNEL_ID, original_msg.video.file_id, caption=original_msg.caption)
            elif original_msg.document:
                await bot.send_document(CHANNEL_ID, original_msg.document.file_id, caption=original_msg.caption)
            else:
                await bot.send_message(CHANNEL_ID, original_msg.text)
            
            await bot.edit_message_text(f"{callback.message.text}\n\n✅ Пост опубликован в канале!", 
                                        chat_id=callback.message.chat.id, 
                                        message_id=callback.message.message_id)
            
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
            await bot.edit_message_text(f"{callback.message.text}\n\n❌ Ошибка публикации: {e}", 
                                        chat_id=callback.message.chat.id, 
                                        message_id=callback.message.message_id)
            await callback.answer("❌ Ошибка!", show_alert=True)
    
    elif action == 'reject':
        await bot.edit_message_text(f"{callback.message.text}\n\n❌ Пост отклонен", 
                                    chat_id=callback.message.chat.id, 
                                    message_id=callback.message.message_id)
        
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

if __name__ == "__main__":
    print("🚀 Бот запущен!")
    print(f"Режим при запуске: {'Модерация' if moderation_mode else 'Прямой постинг'}")
    executor.start_polling(dp, skip_updates=True)