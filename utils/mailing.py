from aiogram import types

from aiogram.utils.exceptions import BotBlocked, ChatNotFound

from create_bot import bot
from database.engine import async_session
from database.queries import (
    get_telegram_ids_content_by_date,
    find_all_referral_telegram_id,
    get_old_paths_content_plan,
)

from logging_errors.logging_setup import logger


async def send_content_to_referrals():
    """
    Рассылает сообщения по контент-плану рефералам пользователей.
    """
    logger.info("*РАССЫЛКА* Вызвана функция send_content_to_referrals")
    try:
        # Удаление старых файлов и записей из БД
        old_file_path = await get_old_paths_content_plan(async_session)
        for file_path in old_file_path:
            try:
                os.remove(file_path)
            except FileNotFoundError:
                logger.debug(f"*РАССЫЛКА* Файл {file_path} не найден.")
                continue

        # Получаем словарь с telegram_id чьим рефералам нужно сегодня отправить
        # рассылку и данными для сообщения
        users_with_content = await get_telegram_ids_content_by_date(async_session)

        # Список словарей со всеми данными для рассылки
        mailing_data = []

        for telegram_id, content in users_with_content.items():
            # Получаем список рефералов пользователя
            referral_telegram_ids = await find_all_referral_telegram_id(
                async_session, telegram_id
            )
            if referral_telegram_ids:
                # Формируем словарь со списком рефералов и данными для смс
                mailing_entry = {
                    "telegram_ids": referral_telegram_ids,
                    "message": content["message"],
                    "media_path": content["media_path"],
                }
                mailing_data.append(mailing_entry)

        for mailing_entry in mailing_data:
            telegram_ids = mailing_entry["telegram_ids"]
            message = mailing_entry["message"]
            media_path = mailing_entry["media_path"]

            if media_path:
                media_extension = Path(media_path).suffix.lower()
                if media_extension in (".jpg", ".jpeg", ".png"):
                    media_type = "photo"
                elif media_extension in (".mp4", ".avi", ".mov"):
                    media_type = "video"
                else:
                    media_type = "document"
            else:
                media_type = None

            for telegram_id in telegram_ids:
                try:
                    if media_type:
                        try:
                            media = types.InputFile(media_path)
                        except FileNotFoundError:
                            logger.debug(f"*РАССЫЛКА* Не найден файл: {media_path}")
                            continue

                        if media_type == "photo":
                            await bot.send_photo(
                                chat_id=telegram_id, photo=media, caption=message
                            )
                        elif media_type == "video":
                            await bot.send_video(
                                chat_id=telegram_id, video=media, caption=message
                            )
                        else:
                            await bot.send_document(
                                chat_id=telegram_id, document=media, caption=message
                            )

                    else:
                        # Отправка сообщения без медиа
                        await bot.send_message(chat_id=telegram_id, text=message)
                except (BotBlocked, ChatNotFound):
                    pass

    except Exception as error:
        logger.exception(
            f"*РАССЫЛКА* Произошла ошибка в функции send_content_to_referrals: {error}"
        )
