from datetime import datetime, timedelta, date
from collections import defaultdict
from typing import Optional

from database.models import Users, ReferralInfo, Invitations, ContentPlan
from logging_errors.logging_setup import logger

from sqlalchemy import select, exists, cast, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.expression import and_


async def create_user(
    session_maker,
    telegram_id: str,
    username: str,
    name: str,
    date_of_reg: datetime,
    user_url: str,
    referral_url: str,
    referrer_id: str,
) -> Optional[True]:
    """
    Создает пользователя в таблице Users.

    Параметры:
    - telegram_id (str): ID пользователя в Telegram.
    - username (str): логин пользователя в Telegram.
    - name (str): имя пользователя.
    - date_of_reg (datetime): дата добавления пользователя в таблицу Users.
    - user_url (str): ссылка на пользователя.
    - referral_url (str): реферальная ссылка пользователя.
    - referrer_id (str): ID реферера.

    Примечания:
    - Проверяет существование пользователя в базе данных по telegram_id.
    - Если пользователь не существует, создает нового пользователя и его реферальную связь.
    - Если пользователь уже существует, выводит сообщение 'ТАКОЙ ПОЛЬЗОВАТЕЛЬ УЖЕ ЕСТЬ В БД'.

    Возвращает:
    - True - если пользователь создан.
    При ошибке - None.
    """
    logger.info("*БД* Вызвана функция create_user")
    try:
        async with session_maker() as session:
            async with session.begin():
                # Проверка существования пользователя в базе данных
                user_exists = await check_user_in_db(session_maker, telegram_id)

                if not user_exists:
                    # Создание нового пользователя и его реферальной связи
                    new_user = Users(
                        telegram_id=telegram_id,
                        username=username,
                        name=name,
                        date_of_reg=date_of_reg,
                        user_url=user_url,
                        referral_url=referral_url,
                        invitation=Invitations(
                            referrer=referrer_id, referral=telegram_id
                        ),
                    )
                    session.add(new_user)
                return True
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции create_user: {error}")


async def create_user_non_referrer(
    session_maker,
    telegram_id: str,
    username: str,
    name: str,
    date_of_reg: datetime,
    user_url: str,
    referral_url: str,
) -> None:
    """
    Создает пользователя в таблице Users, который пришел без реферера.
    """
    logger.info("*БД* Вызвана функция create_user_non_referrer")
    try:
        async with session_maker() as session:
            async with session.begin():
                # Проверка существования пользователя в базе данных
                user_exists = await check_user_in_db(session_maker, telegram_id)

                if not user_exists:
                    # Создание нового пользователя
                    new_user = Users(
                        telegram_id=telegram_id,
                        username=username,
                        name=name,
                        date_of_reg=date_of_reg,
                        user_url=user_url,
                        referral_url=referral_url,
                    )

                    session.add(new_user)
                else:
                    print("ПОЛЬЗОВАТЕЛЬ УЖЕ ЕСТЬ В БД")
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции create_user_non_referrer: {error}"
        )


async def check_user_in_db(session_maker, telegram_id: str) -> Optional[bool]:
    """
    Проверяет наличие пользователя в таблице Users по telegram_id.

    Параметры:
    - telegram_id (str): ID пользователя в Telegram.

    Возвращает:
    - True, если пользователь с заданным telegram_id существует в БД, иначе False.
    При ошибке - None.
    """
    if telegram_id in ["", None]:
        return False
    logger.info("*БД* Вызвана функция check_user_in_db")
    try:
        async with session_maker() as session:
            query = select(exists().where(Users.telegram_id == telegram_id))
            user_exists = await session.scalar(query)
            return user_exists
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции check_user_in_db: {error}")


async def get_referrer_id(session_maker, telegram_id: str) -> Optional[str] | False:
    """
    Получает идентификатор реферера по telegram_id.

    Параметры:
    - telegram_id (str): ID пользователя в Telegram.

    Возвращает:
    - telegram_id реферера или None, если реферер не найден.
    При ошибке - False.
    """

    logger.info("*БД* Вызвана функция get_referrer_id")
    try:
        async with session_maker() as session:
            query = select(Invitations.referrer).where(
                Invitations.referral == telegram_id
            )
            result = await session.execute(query)
            referrer = result.scalar_one_or_none()

            return referrer
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции get_referrer_id: {error}")
        return False


async def find_all_referral_telegram_id(session_maker, telegram_id: str) -> list[str]:
    """
    Ищет telegram_id рефералов всех уровней пользователя по telegram_id. \
    Поиск происходит по условиям:
     - рефералы 1-го уровня добавляются независимо от изменения прив-го сообщения, то же самое
     с рефералами рефералов
     - если реферал (2-го уровня и выше) не изменил приветственное сообщение, то добавляется,
     если изменил, то не добавляется

    Пример:
    Я пригласил тебя и Петю, ты пригласил Васю, Петя пригласил Сашу.
    Ты скопировал бота, Петя не скопировал, Саша скопировал.
    В список всех моих рефералов попадают: ты, Петя(независимо от того копировали вы бота или нет)
     и Саша(т.к. Петя не копировал бота).

    Параметры:
    - telegram_id (str): ID пользователя в Telegram.

    Возвращает:
    - Список telegram_id рефералов всех уровней для пользователя. Если рефералов нет, вернёт [].
    """
    logger.info("*БД* Вызвана функция find_all_referral_telegram_id")
    try:
        async with session_maker() as session:
            referrals = []
            stack = [telegram_id]

            while stack:
                referrer_id = stack.pop()
                query = (
                    select(Users)
                    .join(Invitations, Users.telegram_id == Invitations.referral)
                    .where(Invitations.referrer == referrer_id)
                )
                result = await session.execute(query)

                for user in result.scalars():
                    if user.referral_message_changed:
                        referrals.append(user.telegram_id)
                    else:
                        referrals.append(user.telegram_id)
                        stack.append(user.telegram_id)

            return referrals
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в find_all_referral_telegram_id create_user: {error}"
        )


async def find_user_urls(session_maker, telegram_ids: list[str]) -> list[str]:
    """
    Ищет user_url всех пользователей из таблицы Users по списку telegram_ids.

    Параметры:
    - telegram_ids (list[str]): список ID пользователей в Telegram.

    Возвращает:
    - Список user_url всех найденных пользователей. Если пользователей нет, вернет [].
    """

    logger.info("*БД* Вызвана функция find_user_urls")
    try:
        async with session_maker() as session:
            query = select(Users.user_url).where(Users.telegram_id.in_(telegram_ids))
            result = await session.execute(query)
            user_urls = [row for row in result.scalars()]
            return user_urls
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции find_user_urls: {error}")


async def find_all_referral_user_urls(session_maker, telegram_id: str) -> list[str]:
    """
    Ищет user_url рефералов всех уровней пользователя по заданному telegram_id.

    Параметры:
    - telegram_id (str): ID пользователя в Telegram.

    Возвращает:
    - Список user_url всех рефералов всех уровней пользователя. Если рефералов нет, вернет [].
    """

    logger.info("*БД* Вызвана функция find_all_referral_user_urls")
    try:
        # Ищем рефералов всех уровней для заданного telegram_id
        referrals = await find_all_referral_telegram_id(session_maker, telegram_id)
        # Ищем user_url рефералов
        user_urls = await find_user_urls(session_maker, referrals)

        return user_urls
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции find_all_referral_user_urls: {error}"
        )


async def find_all_referral_telegram_id_to_change_msg(
    session_maker, telegram_id: str
) -> list[str]:
    """
    Ищет telegram_id рефералов всех уровней пользователя по telegram_id, у которых необходимо
     изменить приветственное сообщение.

    Параметры:
    - telegram_id (str): ID пользователя в Telegram.

    Возвращает:
    - Список telegram_id рефералов всех уровней для смены приветственного сообщения.
     Если таких рефералов нет, вернёт [].
    """

    logger.info("*БД* Вызвана функция find_all_referral_telegram_id_to_change_msg")
    try:
        async with session_maker() as session:
            # Список для хранения всех рефералов
            referrals = []
            # Список для обхода рефералов
            stack = [telegram_id]

            while stack:
                referrer_id = stack.pop()
                query = (
                    select(Invitations)
                    .join(Users, Invitations.referral == Users.telegram_id)
                    .where(Invitations.referrer == referrer_id)
                    .where(Users.referral_message_changed.is_(False))
                )
                result = await session.execute(query)

                for invitation in result.scalars():
                    referrals.append(invitation.referral)
                    stack.append(invitation.referral)
            return referrals
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции find_all_referral_telegram_id_to_change_msg:"
            f" {error}"
        )


async def add_referral_info_for_message(
    session_maker, telegram_ids: list | str, real_name: str, user_url_for_message: str
) -> Optional[True]:
    """
    Обновляет информацию о пользователях/ле в таблице ReferralInfo для заданного telegram_ids.
    Если связь с таблицей ReferralInfo уже существует, обновляет поля
     real_name и user_url_for_message.
    Если связь отсутствует, создает новую запись в таблице ReferralInfo и связывает ее с Users.

    Параметры:
    - telegram_ids (list | str): Список|str ID пользователей/ля в Telegram
    - real_name (str): Настоящее имя пользователя для приветственного сообщения рефералу.
    - user_url_for_message (str): Ссылка на пользователя для приветственного сообщения рефералу.

    Возвращает:
    - True - если обновили информацию.
    При ошибке - None.
    """

    logger.info("*БД* Вызвана функция add_referral_info_for_message")
    try:
        async with session_maker() as session:
            async with session.begin():
                if isinstance(telegram_ids, str):
                    telegram_ids = [telegram_ids]

                query = (
                    select(Users)
                    .options(selectinload(Users.referral_info))
                    .where(Users.telegram_id.in_(telegram_ids))
                )
                users = await session.execute(query)
                users = users.scalars().all()
                for user in users:
                    if user:
                        referral_info = user.referral_info
                        # Если есть связь с ReferralInfo, то обновляем данные в таблице ReferralInfo
                        if referral_info:
                            referral_info.real_name = real_name
                            referral_info.user_url_for_message = user_url_for_message
                        # Если связь с таблицей ReferralInfo отсутствует, создаем новую запись
                        else:
                            referral_info = ReferralInfo(
                                real_name=real_name,
                                user_url_for_message=user_url_for_message,
                            )
                            user.referral_info = referral_info
                            session.add(referral_info)
                    else:
                        pass
                return True
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции add_referral_info_for_message: {error}"
        )


async def update_referral_message_changed(
    session_maker, telegram_id: str, referral_message_changed: bool
) -> None:
    """
    Обновляет значение столбца referral_message_changed в таблице Users.

    Параметры:
    - telegram_id: ID Telegram пользователя.
    - referral_message_changed (bool): Новое значение столбца referral_message_changed таблицы Users

    Возвращает:
        None
    """

    logger.info("*БД* Вызвана функция update_referral_message_changed")
    try:
        async with session_maker() as session:
            async with session.begin():
                query = select(Users).where(Users.telegram_id == telegram_id)
                user = await session.execute(query)
                user = user.scalar_one_or_none()
                # Обновляем значение столбца referral_message_changed
                if user:
                    user.referral_message_changed = referral_message_changed
                else:
                    print(f"Пользователь {telegram_id} не найден")
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_referral_message_changed: {error}"
        )


async def get_referral_info_url_and_name(
    session_maker, telegram_id: str
) -> tuple[str, str] | tuple[None, None]:
    """
    Получает user_url_for_message(Ссылка на пользователя для сообщения рефералу)
     и real_name(настоящее имя для сообщения рефералу) пользователя по telegram_id.

    Параметры:
    - telegram_id (str): ID пользователя в Telegram.

    Возвращает:
    - Кортеж (referral_url: str, real_name: str) с user_url_for_message и real_name пользователя.
    - Если у пользователя нет информации для сообщения в таблице ReferralInfo, то вернет
    ('Ссылка неизвестна', 'Имя неизвестно').
    - Если пользователя нет в таблице Users, то вернет ('Реферера нет в БД', 'Реферера нет в БД').
    При ошибке - (None, None).
    """

    logger.info("*БД* Вызвана функция get_referral_info_url_and_name")
    try:
        async with session_maker() as session:
            query = (
                select(Users)
                .where(Users.telegram_id == telegram_id)
                .options(selectinload(Users.referral_info))
            )
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            if user:
                referral_info = user.referral_info
                if referral_info:
                    referral_url = referral_info.user_url_for_message
                    real_name = referral_info.real_name
                else:
                    referral_url = "Ссылка неизвестна"
                    real_name = "Имя неизвестно"

            else:
                referral_url = "У вас нет реферера"
                real_name = "У вас нет реферера"

            return referral_url, real_name
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_referral_info_url_and_name: {error}"
        )
        return None, None


async def get_all_telegram_ids(session_maker) -> list[str]:
    """
    Получает список всех telegram_id из таблицы Users.

    Возвращает:
    - Список всех telegram_id (str) из таблицы Users.
    """

    logger.info("*БД* Вызвана функция get_all_telegram_ids")
    try:
        async with session_maker() as session:
            query = select(Users.telegram_id)
            results = await session.execute(query)
            telegram_ids = [result[0] for result in results]

            return telegram_ids
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_all_telegram_ids: {error}"
        )


async def get_user_url(session_maker, telegram_id: str) -> str:
    """
    Получает user_url (ссылка на пользователя) из таблицы Users по telegram_id.

    Параметры:
    - telegram_id (str): ID пользователя в Telegram.

    Возвращает:
    - Строка с user_url (ссылка на пользователя).
    """

    logger.info("*БД* Вызвана функция get_user_url")
    try:
        async with session_maker() as session:
            query = select(Users).where(Users.telegram_id == telegram_id)
            result = await session.execute(query)
            user = result.scalar_one()
            return user.user_url
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции get_user_url: {error}")


async def get_date_of_reg(session_maker, telegram_id: str) -> datetime:
    """
    Получает date_of_reg (дата добавления в БД) из таблицы Users по telegram_id.

    Параметры:
    - telegram_id (str): ID пользователя в Telegram.

    Возвращает:
    - Объект datetime со временем и датой добавления пользователя в БД.
    """

    logger.info("*БД* Вызвана функция get_date_of_reg")
    try:
        async with session_maker() as session:
            query = select(Users).where(Users.telegram_id == telegram_id)
            result = await session.execute(query)
            user = result.scalar_one()
            return user.date_of_reg
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции get_date_of_reg: {error}")


async def get_telegram_ids_for_mailing(
    session_maker, days_for_mailing: int
) -> dict[int, list[str]]:
    """
    Получает словарь {дни: [telegram_id пользователей]} для рассылки по условию:
     если date_of_reg(дата регистрации пользователя) больше чем (текущая дата - days_for_mailing)
     и меньше чем текущая дата.

    Примечание:
    Ключ с количеством дней создается только, если есть хотя бы 1 пользователь,
     который попадает под условие, иначе ключ не будет создан

    Аргументы:
    - days_for_mailing (int): Количество дней для рассылки.

    Возвращает:
    - Словарь, где ключами являются количество дней с момента регистрации (int),
     а значениями - список telegram_id пользователей (list[str]).
    Если пользователи не найдены, возвращается пустой словарь {}.
    """

    days_for_mailing += 1
    logger.info("*БД* Вызвана функция get_telegram_ids_for_mailing")

    try:
        async with session_maker() as session:
            target_date = date.today() - timedelta(days=days_for_mailing)
            target_date_time = datetime.combine(target_date, datetime.min.time())
            date_today_time = datetime.combine(date.today(), datetime.min.time())

            query = select(Users.telegram_id, Users.date_of_reg).where(
                and_(
                    Users.date_of_reg > target_date_time,
                    Users.date_of_reg < date_today_time,
                )
            )
            result = await session.execute(query)

            telegram_ids = defaultdict(list)
            for row in result:
                count_days = (date.today() - row[1].date()).days
                telegram_ids[count_days].append(row[0])

            return dict(telegram_ids)

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_telegram_ids_for_mailing: {error}"
        )


async def get_referral_message_changed(
    session_maker, telegram_id: str
) -> Optional[bool]:
    """
    Получает referral_message_changed (флаг об изменении приветственного сообщения)
     из таблицы Users по telegram_id.

    Параметры:
    - telegram_id (str): ID пользователя в Telegram.

    Возвращает:
    - True, если пользователь с заданным telegram_id присутствует в БД и
    менял приветственное сообщение, иначе False.
    При ошибке - None.
    """

    logger.info("*БД* Вызвана функция get_referral_message_changed")
    try:
        async with session_maker() as session:
            if await check_user_in_db(session_maker, telegram_id):
                query = select(Users).where(Users.telegram_id == telegram_id)
                result = await session.execute(query)
                user = result.scalar_one()

                return user.referral_message_changed
            return False
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_referral_message_changed: {error}"
        )


async def validate_date(value) -> bool:
    """
    Проверяет, что value является объектом date.

    Параметры:
    - date: Значение для проверки.

    Возвращает:
    - True - если дата является объектом date, иначе False.
    """
    value_is_date = isinstance(value, date)
    value_is_datetime = isinstance(value, datetime)
    if not value_is_date or value_is_datetime:
        return False
    return True


async def create_content_plan_message(
    session_maker,
    telegram_id: str,
    message: str,
    publish_date: date,
    media_path: str | None = None,
) -> int:
    """
    Создает сообщение для контент-плана.

    Параметры:
    - telegram_id (str): ID пользователя в Telegram.
    - message (str): Текст сообщения для рассылки.
    - publish_date (date): Дата, когда сообщение нужно отправить на рассылку.
    - media_path (str): Путь к файлу для рассылки.

    Примечания:
    - Запись о сообщении не будет создано при условиях:
        1) Если publish_date не в формате даты;
        2) Если пользователь не существует в Users;
        3) Если у пользователя уже есть сообщение на дату publish_date.

    Возвращает:
    - 0 - сообщение создано.
    - 1 - publish_date не в формате даты.
    - 2 - пользователь не существует в Users.
    - 3 - у пользователя уже есть сообщение на дату publish_date.
    - -1 - произошла неизвестная ошибка.
    """

    logger.info("*БД* Вызвана функция create_content_plan_message")
    try:
        async with session_maker() as session:
            async with session.begin():
                # # Проверка publish_date является объектом date
                publish_date_is_date = await validate_date(publish_date)
                print(publish_date_is_date)
                if not publish_date_is_date:
                    return 1  # Код ошибки для неверного формата publish_date

                # # Проверка существования пользователя в базе данных
                user_exists = await check_user_in_db(session_maker, telegram_id)
                if not user_exists:
                    return 2  # Код ошибки для отсутствующего пользователя

                # # Проверка существования сообщения с датой publish_date
                query = select(
                    exists().where(
                        and_(
                            ContentPlan.telegram_id == telegram_id,
                            ContentPlan.publish_date == publish_date,
                        )
                    )
                )
                message_date_exists = await session.scalar(query)
                if message_date_exists:
                    return 3  # Код ошибки для дубликата сообщения на эту дату

                # Создание сообщения для контент-плана
                new_message = ContentPlan(
                    telegram_id=telegram_id,
                    message=message,
                    publish_date=publish_date,
                    media_path=media_path,
                )
                session.add(new_message)
                return 0

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции create_content_plan_message: {error}"
        )
        return -1  # Код ошибки для общей ошибки


async def get_content_plan_messages(session_maker, telegram_id: str) -> list[dict]:
    """
    Получает список словарей с сообщениями для контент-плана.

    Параметры:
    - telegram_id (str): ID пользователя в Telegram.

    Возвращает:
    - Список словарей, каждый словарь это одно сообщение пользователя, вида:
    {"message": str, "media_path": str | None, "publish_date": str}, если сообщение
    не содержит медиа, то media_path будет None.

    - Если у пользователя нет сообщений, вернёт [].
    """

    logger.info("*БД* Вызвана функция get_content_plan_messages")
    try:
        async with session_maker() as session:
            query = select(ContentPlan).where(ContentPlan.telegram_id == telegram_id)
            result = await session.execute(query)
            messages = []
            for row in result.scalars():
                message_data = {
                    "message": row.message,
                    "media_path": row.media_path,
                    "publish_date": row.publish_date.strftime("%d.%m.%Y"),
                }
                messages.append(message_data)
            return messages
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_content_plan_messages: {error}"
        )


async def delete_content_plan_message(
    session_maker, telegram_id: str, publish_date: date
) -> int:
    """
    Удаляет сообщение из контент-плана на заданную дату для указанного telegram_id.

    Параметры:
    - telegram_id (str): ID пользователя в Telegram.
    - publish_date (date): Дата, когда сообщение нужно отправить на рассылку.

    Возвращает:
    - True, если сообщение удалено.
    - False, если сообщение не было найдено или произошла ошибка при удалении.
    Возвращает:
    - 0 - сообщение удалено.
    - 1 - publish_date не в формате даты.
    - 2 - сообщение не существует в БД.
    - -1 - произошла неизвестная ошибка.
    """
    logger.info("*БД* Вызвана функция delete_content_plan_message")
    try:
        async with session_maker() as session:
            async with session.begin():
                # # Проверка publish_date является объектом date
                publish_date_is_date = await validate_date(publish_date)
                if not publish_date_is_date:
                    return 1  # Код ошибки для неверного формата publish_date

                query = delete(ContentPlan).where(
                    and_(
                        ContentPlan.telegram_id == telegram_id,
                        ContentPlan.publish_date == publish_date,
                    )
                )
                result = await session.execute(query)
                change_row_count = result.rowcount
                if change_row_count == 0:
                    return 2  # Код ошибки для отсутствующего сообщения
                if change_row_count >= 1:
                    return 0
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции delete_content_plan_message: {error}"
        )
        return -1  # Код ошибки для общей ошибки


async def get_telegram_ids_content_by_date(session_maker) -> dict:
    """
    Получает словарь, где ключами являются telegram_id пользователей, рефералам
     которых нужно сегодня отправить рассылку по контент-плану, а значениями - сообщения.

    Возвращает:
    - Словарь вида {"telegram_id": {"message": str, "media_path": str | None}}, если сообщение
    не содержит медиа, то media_path будет None.
    - Если нет сообщений для сегодняшней рассылки, вернёт {}.
    """
    logger.info("*БД* Вызвана функция get_telegram_ids_content_by_date")
    try:
        async with session_maker() as session:
            date_today = date.today()
            query = select(ContentPlan).where(ContentPlan.publish_date == date_today)
            result = await session.execute(query)

            messages = {}
            for row in result.scalars():
                messages[row.telegram_id] = {
                    "message": row.message,
                    "media_path": row.media_path,
                }
            return messages

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_telegram_ids_content_by_date: {error}"
        )


async def get_old_paths_content_plan(session_maker) -> list[str]:
    """
    Получает список путей к файлам контент-плана и удаляет записи из таблицы ContentPlan,
     у которых значение publish_date раньше текущей даты.

    Возвращает:
    - list[str]: Список media_path удаленных записей.
    """
    logger.info("*БД* Вызвана функция get_old_paths_content_plan")
    try:
        async with session_maker() as session:
            # Получаем записи, у которых publish_date раньше сегодняшней даты
            query = select(ContentPlan).where(ContentPlan.publish_date < date.today())
            result = await session.execute(query)
            old_content_plans = result.scalars().all()

            # Удаляем найденные записи и записываем media_path перед удалением
            deleted_media_paths = []
            for content_plan in old_content_plans:
                if content_plan.media_path:
                    deleted_media_paths.append(content_plan.media_path)
                await session.delete(content_plan)
            await session.commit()

        return deleted_media_paths
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_old_paths_content_plan: {error}"
        )
