"""
Script para testar o bot localmente usando polling (sem webhook).
Encaminha updates para o endpoint local.
Uso: python test_telegram_local.py
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")
LOCAL_URL = "http://localhost:8000/api/webhook/telegram"


async def poll():
    offset = 0
    print(f"🤖 Polling bot {BOT_TOKEN[:10]}...")
    print(f"📡 Forwarding to {LOCAL_URL}")
    print("Press Ctrl+C to stop\n")

    async with httpx.AsyncClient(timeout=60) as client:
        # Deletar webhook existente para permitir polling
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
        )

        while True:
            try:
                resp = await client.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                )
                data = resp.json()

                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    print(f"📨 Update {update['update_id']}")

                    # Encaminhar para endpoint local
                    try:
                        r = await client.post(
                            LOCAL_URL,
                            json=update,
                            headers={"X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET},
                        )
                        print(f"   → {r.status_code}")
                    except Exception as e:
                        print(f"   ❌ {e}")

            except httpx.ReadTimeout:
                continue
            except KeyboardInterrupt:
                break


if __name__ == "__main__":
    asyncio.run(poll())
