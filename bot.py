import asyncio
from aiogram import Bot, Dispatcher, types
import datetime
import re

API_TOKEN = " " # токен
GROUP1_ID = -  # группа

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# -------------------- ВРЕМЯ ЗАПУСКА --------------------
BOT_START_TIME = datetime.datetime.now(datetime.timezone.utc)

# -------------------- ФИЛЬТР ПО ПОДПИСИ --------------------
SIGNATURE_PATTERN = re.compile(
    r"---\s*Подпишись\s+@best_(?:svao|vao).*Дежурный админ @top_admin_msk.*размещаем анонимно", # "подвал" у каждого новостного поста
    re.IGNORECASE | re.DOTALL
)

def has_signature(text: str) -> bool:
    if not text:
        return False
    clean_text = re.sub(r"\s+", " ", text)
    return bool(SIGNATURE_PATTERN.search(clean_text))

# -------------------- ОБРАБОТКА ТЕКСТА --------------------
def normalize_yo(text: str) -> str:
    return text.replace("ё", "е").replace("Ё", "Е")

def process_text(text: str) -> str:
    """Меняем ё→е и @best_vao→@best_svao"""
    text = normalize_yo(text)
    text = text.replace("@best_vao", "@best_svao")
    return text

def normalize_text_with_entities(text: str, entities: list[types.MessageEntity] | None) -> tuple[str, list[types.MessageEntity] | None]:
    """
    Меняет ё→е в тексте и сохраняет Telegram-entities.
    """
    if not text:
        return text, entities
    if not entities:
        return process_text(text), None

    text_chars = list(text)
    for i, c in enumerate(text_chars):
        if c == "ё":
            text_chars[i] = "е"
        elif c == "Ё":
            text_chars[i] = "Е"
    new_text = "".join(text_chars)
    new_text = new_text.replace("@best_vao", "@best_svao")

    return new_text, entities

# -------------------- ХРАНИЛИЩЕ ДЛЯ АЛЬБОМОВ --------------------
media_groups = {}  # {media_group_id: [messages]}

# -------------------- ОБРАБОТКА СООБЩЕНИЙ --------------------
@dp.message()
async def handler(message: types.Message):
    # Пропускаем старые сообщения
    msg_date = message.date
    if msg_date.tzinfo is None:
        msg_date = msg_date.replace(tzinfo=datetime.timezone.utc)
    if msg_date < BOT_START_TIME:
        return

    # -------------------- ОБРАБОТКА АЛЬБОМА --------------------
    if message.media_group_id:
        mgid = message.media_group_id
        if mgid not in media_groups:
            media_groups[mgid] = []

        media_groups[mgid].append(message)
        await asyncio.sleep(0.5)

        # Минимум 2 элемента для альбома
        if len(media_groups[mgid]) < 2:
            return

        messages = media_groups.pop(mgid)
        caption = messages[0].caption or ""
        if not has_signature(caption):
            return
        fixed_caption, entities = normalize_text_with_entities(caption, messages[0].caption_entities)

        media = []
        for i, msg in enumerate(messages):
            if msg.photo:
                file_id = msg.photo[-1].file_id
                media.append(types.InputMediaPhoto(
                    media=file_id,
                    caption=fixed_caption if i == 0 else None,
                    caption_entities=entities if i == 0 else None
                ))
            elif msg.video:
                file_id = msg.video.file_id
                media.append(types.InputMediaVideo(
                    media=file_id,
                    caption=fixed_caption if i == 0 else None,
                    caption_entities=entities if i == 0 else None
                ))
            elif msg.document:
                file_id = msg.document.file_id
                media.append(types.InputMediaDocument(
                    media=file_id,
                    caption=fixed_caption if i == 0 else None,
                    caption_entities=entities if i == 0 else None
                ))

        await bot.send_media_group(chat_id=messages[0].chat.id, media=media)

        for msg in messages:
            try:
                await msg.delete()
            except:
                pass

        print("[АЛЬБОМ] исправлен и пересобран")
        return

    # -------------------- ОДИНОЧНЫЕ МЕДИА --------------------
    caption = message.caption or ""
    if (message.photo or message.video or message.document) and has_signature(caption):
        fixed_caption, entities = normalize_text_with_entities(message.caption, message.caption_entities)
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            caption=fixed_caption or None,
            caption_entities=entities
        )
        await message.delete()
        print("[ОДИНОЧНОЕ МЕДИА] исправлено")
        return

    # -------------------- ТЕКСТ --------------------
    original_text = message.text or ""
    if original_text and has_signature(original_text):
        fixed_text, entities = normalize_text_with_entities(original_text, message.entities)
        if fixed_text != original_text:
            await message.answer(fixed_text, entities=entities)
            await message.delete()
            print("[ТЕКСТ] исправлено")
            return

# -------------------- ЗАПУСК --------------------
async def main():
    print("[START] Bot is starting…")
    print("BOT_START_TIME:", BOT_START_TIME.isoformat())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
