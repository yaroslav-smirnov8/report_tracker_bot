# Инструкция: добавление бота в группу и проверка функций

## Предусловия
- Настрой токен окружения: переменная `BOT_TOKEN` должна быть доступна процессу. Конфиг читает `.env`, если он есть.
- Не храни токен в репозитории. Если используешь `.env`, убедись, что он не коммитится и добавлен в `.gitignore`. В PowerShell для временного запуска можно выставить:
  - `$env:BOT_TOKEN="ТОКЕН"`
- База данных доступна и инициализируется при старте: см. [db.py](file:///g:/Progs/Portfolio%20English/rbot/app/core/db.py). Таблицы создаются через `init_db()`. Строка подключения берётся из `DB_URL` в `.env`.
- Запуск бота: `python main.py`. Точка входа — [main.py](file:///g:/Progs/Portfolio%20English/rbot/main.py).

## База данных (MariaDB/MySQL)
- Пример строки подключения для `.env`:
  - `DB_URL=mysql+pymysql://botuser:password@localhost/botdb`
- Создание базы и пользователя:
  - `CREATE DATABASE botdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
  - `CREATE USER 'botuser'@'localhost' IDENTIFIED BY 'password';`
  - `GRANT ALL PRIVILEGES ON botdb.* TO 'botuser'@'localhost';`
  - `FLUSH PRIVILEGES;`
- Ошибка `auth_gssapi_client` означает, что текущий пользователь подключается через GSSAPI-плагин. Решение:
  - Используй отдельного пользователя с паролем, как в примере выше.
  - Проверь активный плагин: `SELECT user, host, plugin FROM mysql.user;`

## Добавление бота в группу
- В @BotFather отключи Privacy Mode: `/setprivacy` → выбери бота → `Disable`. Иначе бот будет видеть только команды, а не обычные сообщения и хэштеги.
- Добавь бота в нужный групповой чат.
- Права:
  - Минимум: «читать» и «отправлять» сообщения.
  - Админ-права нужны только для действий по удалению участников через бота.

## Роли для тестирования
- Удобно иметь 2 аккаунта:
  - Админ — проверяет админ-меню, настройки, удаление участников.
  - Участник — отправляет отчёты с хэштегами, проверяет личные сообщения от бота.

## Команды
- `/start` — приветствие
- `/help` — справка
- `/menu` или `/buttons` — открыть меню действий
- `/status` — текущие настройки чата
- `/join` — зарегистрироваться как участник
- `/setstartdate YYYY-MM-DD` — задать дату старта курса
- `/settimezone Europe/Moscow` — задать часовой пояс чата
- `/remove USER_ID` — удалить участника по ID (только админ)

Регистрация команд: [handlers.py: register_handlers](file:///g:/Progs/Portfolio%20English/rbot/app/handlers/handlers.py#L769-L812).

## Меню и кнопки
- Кнопки участника: Report templates, My progress, Status, Today’s deadlines, Next deadline, FAQ, Help.
- Кнопки администратора: Send report to DM, Set start date, Set timezone, Remove participant.
- Построение меню: [show_buttons](file:///g:/Progs/Portfolio%20English/rbot/app/handlers/handlers.py#L274-L327), обработка: [button](file:///g:/Progs/Portfolio%20English/rbot/app/handlers/handlers.py#L329-L366).

## Настройка курса
- Задай дату старта: `/setstartdate YYYY-MM-DD`.
- Установи часовой пояс: `/settimezone Europe/Moscow`.
- Тексты дедлайнов: [build_today_deadlines_text](file:///g:/Progs/Portfolio%20English/rbot/app/handlers/handlers.py#L95-L132), [build_next_deadline_text](file:///g:/Progs/Portfolio%20English/rbot/app/handlers/handlers.py#L133-L160).

## Отчёты и хэштеги
- Ежедневные: `#morningN`, `#eveningN` — где `N` это номер дня от даты старта.
- Еженедельные (по воскресеньям): `#weekW` — где `W` это номер недели (`ceil(N/7)`).
- Обработка сообщений и хэштегов: [handle_message](file:///g:/Progs/Portfolio%20English/rbot/app/handlers/handlers.py#L652-L743).

## Пошаговое тестирование
- Личка:
  - Отправь `/start`, `/help`, `/menu` — бот должен ответить.
  - В меню нажми “My progress” — бот отправит прогресс в личку.
- Группа:
  - Добавь бота и отключи Privacy Mode.
  - Выполни `/settimezone Europe/Moscow` и `/setstartdate YYYY-MM-DD`.
  - Как участник опубликуй сообщение с `#morningN` или `#eveningN`; в воскресенье — `#weekW`.
  - Проверь:
    - Ответы на кнопки “Today’s deadlines”, “Next deadline”.
    - “Send report to DM” — админ получает Excel-отчёт в личку.
    - Удаление участника: `/remove USER_ID` или через меню “Remove participant”.
  - Добавление/выход участника — бот реагирует на события `new_chat_members` и `left_chat_member`.

## Excel-отчёт
- Админ нажимает “Send report to DM” — отчёт формируется и отправляется в личку: см. [excel_reports](file:///g:/Progs/Portfolio%20English/rbot/app/reports/excel_reports.py).

## Устранение проблем
- Бот не реагирует на хэштеги: проверь, что Privacy Mode — `Disable`.
- Дедлайны «не те»: проверь установленный часовой пояс чата.
- Хэштег в медиа: добавляй хэштеги в подписи — бот обрабатывает и текст, и caption.
- Логи: если журнал не появляется, убедись, что логирование включено и разрешено системой (см. [config.py](file:///g:/Progs/Portfolio%20English/rbot/app/core/config.py)).

## Безопасность токена
- Не публикуй токен. Добавь `.env` в `.gitignore`.
- Для локального запуска без `.env` используй переменную окружения в сессии:
  - PowerShell (только текущий сеанс): `$env:BOT_TOKEN="ТОКЕН"`
  - Постоянно: через системные настройки переменных окружения Windows.
