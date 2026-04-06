import os
import re
import sys
import time
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

    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, cookies=cookies, timeout=30)
            resp.raise_for_status()
            break
        except requests.exceptions.RequestException:
            if attempt == 2:
                return None, None, None, None, "❌ Сайт не отвечает (таймаут)"
            time.sleep(3)

    match = re.search(r'Баланс:\s*<span[^>]*>([\d.,]+\s*грн\.)</span>', resp.text)
    if not match:
        return None, None, None, None, "❌ Не удалось получить баланс (возможно куки умерли)"

    balance = match.group(1).strip()

    tariff_m = re.search(r'Тариф:\s*<b>([^<]+)</b>', resp.text)
    tariff = tariff_m.group(1).strip() if tariff_m else ""

    return balance, None, tariff, None, None


def build_message(balance, tariff):
    try:
        daily_cost = float(re.search(r'([\d.]+)\s*грн\.\s*щодня', tariff).group(1))
        balance_val = float(re.search(r'([\d.]+)', balance).group(1))
        days = balance_val / daily_cost
        return f"💰 Баланс: <b>{balance}</b> (~{days:.1f} дн.)"
    except Exception:
        return f"💰 Баланс: <b>{balance}</b>"


def send_message(chat_id, text, with_button=False):
    token = os.environ["TG_BOT_TOKEN"]

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    if with_button:
        payload["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "🔄 Проверить баланс", "callback_data": "check_balance"}
            ]]
        }

    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json=payload,
        timeout=10
    )


def answer_callback(callback_query_id):
    token = os.environ["TG_BOT_TOKEN"]
    requests.post(
        f"https://api.telegram.org/bot{token}/answerCallbackQuery",
        json={
            "callback_query_id": callback_query_id,
            "text": "Запрашиваю баланс..."
        },
        timeout=10,
    )


def get_updates(offset=None):
    token = os.environ["TG_BOT_TOKEN"]

    params = {
        "timeout": 30,
        "allowed_updates": ["message", "callback_query"]
    }

    if offset:
        params["offset"] = offset

    resp = requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates",
        params=params,
        timeout=35,
    )

    return resp.json().get("result", [])


def run_scheduled():
    chat_id = os.environ["TG_CHAT_ID"]

    balance, _, tariff, _, error = fetch_balance()

    if error:
        send_message(chat_id, error, with_button=True)
        print(error)
        return  # НЕ падаем больше

    msg = build_message(balance, tariff)
    send_message(chat_id, msg, with_button=True)

    print(f"✅ Отправлено: {msg}")


def run_bot():
    chat_id = os.environ["TG_CHAT_ID"]

    print("🤖 Бот запущен...")
    offset = None
    deadline = time.time() + 55

    while time.time() < deadline:
        updates = get_updates(offset)

        for update in updates:
            offset = update["update_id"] + 1

            if "callback_query" in update:
                cb = update["callback_query"]

                if cb.get("data") == "check_balance":
                    answer_callback(cb["id"])

                    balance, _, tariff, _, error = fetch_balance()

                    if error:
                        send_message(chat_id, error, with_button=True)
                    else:
                        msg = build_message(balance, tariff)
                        send_message(chat_id, msg, with_button=True)

            elif "message" in update:
                text = update["message"].get("text", "")

                if text in ("/start", "/balance"):
                    balance, _, tariff, _, error = fetch_balance()

                    if error:
                        send_message(chat_id, error, with_button=True)
                    else:
                        msg = build_message(balance, tariff)
                        send_message(chat_id, msg, with_button=True)

        time.sleep(2)

    print("⏹ Бот остановлен")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "scheduled"

    if mode == "bot":
        run_bot()
    else:
        run_scheduled()
