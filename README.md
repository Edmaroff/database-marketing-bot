# Файлы для работы с базой данных в телеграм-боте для маркетинга 



## Задача
- Спроектировать и создать методы базы данных для работы с реферальной системой, персонализации приветственных сообщений рефералам и возможностью для каждого пользователя составить сообщение для рассылки своим рефералам на любую будущую дату (контент-план), включая текст сообщения и медиафайлы.

## Результаты
- Создал структуру таблиц БД для хранения необходимой информации о пользователях, реферальных связях и контент-плане.
- Реализовал набор функций для создания, обновления, поиска и получения данных пользователей, реферальных связей и контент-плана, а также для реализации персонализации приветственных сообщений рефералам.
- Создал функцию рассылки сообщений рефералам пользователя по контент-плану.
- Обеспечил обработку ошибок и логирование для облегчения отладки и мониторинга.

## Содержание

- `database/models.py`: Определение моделей SQLAlchemy для таблиц базы данных.
- `database/engine.py`: Настройки для подключения к базе данных с использованием SQLAlchemy.
- `database/creation.py`: Функции создания и удаления таблиц.
- `database/queries.py`: Асинхронные функции для работы с базой данных.
- `utils/mailing.py`: Функция рассылки сообщений пользователям по контент-плану.

## Используемые технологии
- SQLAlchemy
- Asyncio