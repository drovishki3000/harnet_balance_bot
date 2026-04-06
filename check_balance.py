
import os
import re
import sys
import time
import requests


def get_session():
    """Логинится на сайте и возвращает сессию с куками."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
    })

    resp = session.post("https://my.harnet.com.ua/user/index.php", data={
        "login":    os.environ["HARNET_LOGIN"],     # номер лицевого счёта, напр. 2404
        "password": os.environ["HARNET_PASSWORD"],  # пароль от личного кабинета
        "type":     "userlogin",
    }, timeout=15)
    resp.raise_for_status()

    if "main.php" not in resp.url and "Баланс" not in resp.text:
        raise RuntimeError("Ошибка входа — проверьте HARNET_LOGIN и HARNET_PASSWORD в Secrets.")

    return session


def fetch_balance():
    try:
        session = get_session()
    except RuntimeError as e:
        return None, None, None, None, f"❌ {e}"

    resp = session.get("https://my.harnet.com.ua/user/main.php", timeout=15)
    resp.raise_for_status()

    match = re.search(r'Баланс:\s*<span[^>]*>([\d.,]+\s*грн\.)</span>', resp.text)
    if not match:
        return None, None, None, None, "❌ Не удалось найти баланс на странице."

    balance  = match.group(1).strip()
    tariff_m = re.search(r'Тариф:\s*<b>([^<]+)</b>', resp.text)
    tariff   = tariff_m.group(1).strip() if tariff_m else ""

    return balance, None, tariff, None, None


def build_message(balance, tariff):
    days_str = ""
    try:
        daily_cost  = float(re.search(r'([\d.]+)\s*грн\.\s*щодня', tariff).group(1))
        balance_val = float(re.search(r'([\d.]+)', balance).group(1))
        days        = int(balance_val / daily_cost)
        days_str    = f"\n📅 Осталось: <b>~{days} дн.</b>"
    except Exception:
        pass
    return f"💰 Баланс: <b>{balance}</b>{days_str}"


def send_message(chat_id, text, with_button=False):
    token = os.environ["TG_BOT_TOKEN"]
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if with_button:
        payload["reply_markup"] = {
            "inline_keyboard": [[
                {"text": "🔄 Проверить баланс", "callback_data": "check_balance"}
            ]]
        }
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json=payload, timeout=10).raise_for_status()


def answer_callback(callback_query_id):
    token = os.environ["TG_BOT_TOKEN"]
    requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery",
        json={"callback_query_id": callback_query_id, "text": "Запрашиваю баланс..."},
        timeout=10)


def get_updates(offset=None):
    token  = os.environ["TG_BOT_TOKEN"]
    params = {"timeout": 25, "allowed_updates": ["message", "callback_query"]}
    if offset:
        params["offset"] = offset
    resp = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("result", [])


def handle_request(chat_id):
    balance, _, tariff, __, error = fetch_balance()
    if error:
        send_message(chat_id, error, with_button=True)
    else:
        send_message(chat_id, build_message(balance, tariff), with_button=True)


def run_scheduled():
    chat_id = os.environ["TG_CHAT_ID"]
    balance, _, tariff, __, error = fetch_balance()
    if error:
        send_message(chat_id, error, with_button=True)
        print(error); sys.exit(1)
    send_message(chat_id, build_message(balance, tariff), with_button=True)
    print(f"✅ Отправлено: {balance}")


def run_bot():
    chat_id  = os.environ["TG_CHAT_ID"]
    offset   = None
    deadline = time.time() + 55
    print("🤖 Слушаю обновления...")
    while time.time() < deadline:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            if "callback_query" in update:
                cb = update["callback_query"]
                if cb.get("data") == "check_balance":
                    answer_callback(cb["id"])
                    handle_request(chat_id)
            elif "message" in update:
                text = update["message"].get("text", "")
                if text in ("/start", "/balance"):
                    handle_request(chat_id)
        time.sleep(2)
    print("⏹ Готово.")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "scheduled"
    if mode == "bot":
        run_bot()
    else:
        run_scheduled()
