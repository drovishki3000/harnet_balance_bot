import os
import re
import sys
import requests

def fetch_balance():
    url = "https://my.harnet.com.ua/user/main.php"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
        "Referer": "https://my.harnet.com.ua/user/index.php",
    }
    cookies = {
        "us_userpass":    os.environ["HARNET_USERPASS"],
        "us_userlogname": os.environ["HARNET_USERLOGNAME"],
        "PHPSESSID":      os.environ["HARNET_PHPSESSID"],
    }

    resp = requests.get(url, headers=headers, cookies=cookies, timeout=15)
    resp.raise_for_status()

    match = re.search(r'Баланс:\s*<span[^>]*>([\d.,]+\s*грн\.)</span>', resp.text)
    if not match:
        return None, None, None, None, "❌ Не удалось получить баланс. Возможно, куки истекли."

    balance    = match.group(1).strip()
    name_m     = re.search(r'<b>([\w\s]+)</b><br>Тариф:', resp.text)
    tariff_m   = re.search(r'Тариф:\s*<b>([^<]+)</b>', resp.text)
    status_m   = re.search(r'Стан:\s*<b>([^<]+)</b>', resp.text)

    name   = name_m.group(1).strip()   if name_m   else "—"
    tariff = tariff_m.group(1).strip() if tariff_m else "—"
    status = status_m.group(1).strip() if status_m else "—"

    return balance, name, tariff, status, None


def build_message(balance, name, tariff, status, source=""):
    try:
        daily_cost = float(re.search(r'([\d.]+)\s*грн\.\s*щодня', tariff).group(1))
        balance_val = float(re.search(r'([\d.]+)', balance).group(1))
        days = balance_val / daily_cost
        return f"💰 Баланс: <b>{balance}</b> (~{days:.1f} дн.)"
    except Exception:
        return f"💰 Баланс: <b>{balance}</b>"


def send_message(chat_id, text, with_button=False):
    token = os.environ["TG_BOT_TOKEN"]
    url   = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": "HTML",
    }
    if with_button:
        payload["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "🔄 Проверить баланс", "callback_data": "check_balance"}
            ]]
        }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()


def answer_callback(callback_query_id):
    token = os.environ["TG_BOT_TOKEN"]
    requests.post(
        f"https://api.telegram.org/bot{token}/answerCallbackQuery",
        json={"callback_query_id": callback_query_id, "text": "Запрашиваю баланс..."},
        timeout=10,
    )


def get_updates(offset=None):
    token = os.environ["TG_BOT_TOKEN"]
    params = {"timeout": 30, "allowed_updates": ["message", "callback_query"]}
    if offset:
        params["offset"] = offset
    resp = requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates",
        params=params,
        timeout=35,
    )
    resp.raise_for_status()
    return resp.json().get("result", [])


def run_scheduled():
    """Запускается по расписанию из GitHub Actions (cron)."""
    chat_id = os.environ["TG_CHAT_ID"]
    balance, name, tariff, status, error = fetch_balance()
    if error:
        send_message(chat_id, error, with_button=True)
        print(error); sys.exit(1)

    msg = build_message(balance, name, tariff, status, source="scheduled")
    send_message(chat_id, msg, with_button=True)
    print(f"✅ Отправлено по расписанию: {balance}")


def run_bot():
    """
    Режим бота — слушает нажатия кнопки и команду /start.
    Запускается отдельным GitHub Actions job (workflow_dispatch или отдельный cron).
    Работает 55 секунд (лимит GitHub Actions шага — 6 часов, но нам хватит цикла).
    """
    import time
    chat_id = os.environ["TG_CHAT_ID"]
    token   = os.environ["TG_BOT_TOKEN"]

    print("🤖 Бот запущен, слушаю обновления...")
    offset    = None
    deadline  = time.time() + 55  # слушаем 55 секунд

    while time.time() < deadline:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1

            # Нажатие inline-кнопки
            if "callback_query" in update:
                cb = update["callback_query"]
                if cb.get("data") == "check_balance":
                    answer_callback(cb["id"])
                    balance, name, tariff, status, error = fetch_balance()
                    if error:
                        send_message(chat_id, error, with_button=True)
                    else:
                        msg = build_message(balance, name, tariff, status, source="button")
                        send_message(chat_id, msg, with_button=True)
                    print(f"✅ Ответил на кнопку: {balance if not error else error}")

            # Команда /start или /balance
            elif "message" in update:
                text = update["message"].get("text", "")
                if text in ("/start", "/balance"):
                    balance, name, tariff, status, error = fetch_balance()
                    if error:
                        send_message(chat_id, error, with_button=True)
                    else:
                        msg = build_message(balance, name, tariff, status, source="button")
                        send_message(chat_id, msg, with_button=True)

        time.sleep(2)

    print("⏹ Сессия бота завершена.")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "scheduled"
    if mode == "bot":
        run_bot()
    else:
        run_scheduled()
