# HarNet Balance Bot 🌐

Telegram-бот который:
- **Каждый день в 09:00** присылает баланс HarNet
- **По нажатию кнопки** «🔄 Проверить баланс» — отвечает сразу (задержка до 2 минут)
- Работает **бесплатно** через GitHub Actions

---

## Структура файлов

```
harnet-balance-bot/
├── check_balance.py
└── .github/
    └── workflows/
        └── balance.yml
```

---

## Настройка

### 1. Создать Telegram-бота

1. Напишите [@BotFather](https://t.me/BotFather) → `/newbot`
2. Скопируйте **токен**: `7123456789:AAHxxx...`

### 2. Узнать свой chat_id

1. Напишите боту `/start`
2. Откройте в браузере:
   ```
   https://api.telegram.org/bot<ВАШ_ТОКЕН>/getUpdates
   ```
3. Найдите `"id"` внутри `"chat"` — это ваш `chat_id`

### 3. Создать приватный репозиторий на GitHub

Загрузите файлы сохраняя структуру папок.

### 4. Добавить секреты

**Settings → Secrets and variables → Actions → New repository secret**

| Имя                  | Значение                            |
|----------------------|-------------------------------------|
| `HARNET_USERPASS`    | значение куки `us_userpass`         |
| `HARNET_USERLOGNAME` | значение куки `us_userlogname`      |
| `HARNET_PHPSESSID`   | значение куки `PHPSESSID`           |
| `TG_BOT_TOKEN`       | токен от BotFather                  |
| `TG_CHAT_ID`         | ваш числовой chat_id                |

### 5. Включить Actions

В репозитории: **Actions → Enable Actions**

Затем запустите вручную: **Actions → HarNet Balance Bot → Run workflow**

---

## Как работает кнопка

GitHub Actions запускается каждые 2 минуты и слушает нажатия кнопки 55 секунд.
Максимальная задержка между нажатием и ответом — **~2 минуты**.

---

## Команды бота

- `/start` или `/balance` — запросить баланс
- Кнопка **🔄 Проверить баланс** под любым сообщением

---

## ⚠️ Обновление куков

Куки истекают раз в несколько недель. Когда придёт ошибка:
1. Войдите на my.harnet.com.ua в браузере
2. DevTools (F12) → Application → Cookies
3. Скопируйте новые значения в Secrets GitHub
