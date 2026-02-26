## Запуск бота

### Требования
- Python 3.x
- MySQL

### Зависимости Python
Установите зависимости вручную, т.к. файла requirements нет:

```bash
pip install python-telegram-bot==13.* apscheduler sqlalchemy pymysql pytz openpyxl
```

### База данных
По умолчанию используется подключение из app/core/db.py:

```
mysql+pymysql://root:123@localhost/botdb
```

Убедитесь, что база `botdb` существует и доступна, либо измените строку подключения в [db.py](file:///g:/Progs/Portfolio%20English/rbot/app/core/db.py#L1-L6).

### Переменные окружения
Установите токен бота:

```bash
setx BOT_TOKEN "YOUR_TELEGRAM_BOT_TOKEN"
```

После установки переменной перезапустите терминал.

### Запуск
```bash
python main.py
```

При первом запуске таблицы создаются автоматически через SQLAlchemy.
