from sqlalchemy import Column, Integer, Boolean, String, ForeignKey, DateTime, Date
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Users(Base):
    """
    Таблица с информацией о пользователе

    Атрибуты:
    - user_id (int): Уникальный идентификатор пользователя
    - telegram_id (str): ID пользователя в Telegram.
    - username (str): Логин пользователя
    - name (str): Имя пользователя
    - date_of_reg (datetime): Дата добавления пользователя в таблицу
    - user_url (str): Ссылка на пользователя
    - is_referral (bool): Флаг, указывающий, участвует ли пользователь в реферальной программе.
     True - участвует, False - не участвует.
    - referral_message_changed (bool): Флаг, указывающий, менял ли пользователь
      реферальное сообщение. True - менял, False - не менял.
    - referral_url (str): Реферальная ссылка пользователя

    - info_ref_id (int): Внешний ключ для связи с таблицей ReferralInfo
    - referral_info (ReferralInfo): Объект связи с таблицей ReferralInfo

    - invitation_id (int): Внешний ключ для связи с таблицей Invitations
    - invitation (Invitations): Объект связи с таблицей Invitations
    """

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)

    # telegram_id = Column(Integer, unique=True, nullable=False)
    telegram_id = Column(String, unique=True, nullable=False)

    username = Column(String(35), nullable=True)
    name = Column(String(130), nullable=True)
    date_of_reg = Column(DateTime, nullable=False)
    user_url = Column(String(50))
    # Флаг, указывающий, участвует ли пользователь в реф-ой программе
    is_referral = Column(Boolean, default=False, nullable=False)
    # Флаг, указывающий, менял ли пользователь реферальное сообщение
    referral_message_changed = Column(Boolean, default=False, nullable=False)
    referral_url = Column(String(100), nullable=False)

    # Внешний ключ для связи (один к одному) с таблицей "ReferralInfo"
    info_ref_id = Column(Integer, ForeignKey("referral_info.info_id"), nullable=True)
    referral_info = relationship(
        "ReferralInfo", backref="user", foreign_keys=[info_ref_id], uselist=False
    )

    # Внешний ключ для связи с таблицей "Invitations"
    invitation_id = Column(Integer, ForeignKey("invitations.id"), nullable=True)
    invitation = relationship(
        "Invitations", backref="user_invitation", foreign_keys=[invitation_id]
    )


class Invitations(Base):
    """
    Таблица с telegram_id реферала и реферера

    Атрибуты:
    - id (int): Уникальный идентификатор записи
    - referrer (str): Telegram ID реферера (тот кто пригласил)
    - referral (str): Telegram ID реферала (тот кого пригласили)
    """

    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True)

    referrer = Column(String, nullable=False)
    referral = Column(String, nullable=False, unique=True)


class ReferralInfo(Base):
    """
    Таблица с информацией для приветственного сообщения рефералу.

    Атрибуты:
    - info_id (int): Уникальный идентификатор записи
    - real_name (str): Реальное имя пользователя для сообщения
    - user_url_for_message (str): Ссылка на пользователя для сообщения
    """

    __tablename__ = "referral_info"

    info_id = Column(Integer, primary_key=True)

    real_name = Column(String(60), nullable=False)
    user_url_for_message = Column(String(100), nullable=False)


class ContentPlan(Base):
    """
    Таблица с информацией для рассылок (контент-плана) всем рефералам пользователя.

    Атрибуты:
    - content_id (int): Уникальный идентификатор записи
    - telegram_id (str): Telegram ID пользователя, который создает контент-план.
    - message (str): Текст сообщения для рассылки.
    - media_path (str): Путь к файлу для рассылки.
    - publish_date (date): Дата, когда сообщение должно отправиться.
    """

    __tablename__ = "content_plan"

    content_id = Column(Integer, primary_key=True)

    telegram_id = Column(String(35), unique=False, nullable=False)
    message = Column(String(1200), nullable=False)
    media_path = Column(String(400), nullable=True)
    publish_date = Column(Date, nullable=False)
