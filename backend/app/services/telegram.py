import httpx
from app.config import settings

TELEGRAM_API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


async def send_message(chat_id: int, text: str, parse_mode: str | None = "Markdown", reply_markup: dict | None = None):
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)


async def get_file_url(file_id: str) -> tuple[str, str]:
    """Retorna (download_url, extensão)."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id})
        resp.raise_for_status()
        file_path = resp.json()["result"]["file_path"]
        ext = file_path.split(".")[-1] if "." in file_path else "ogg"
        url = f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}"
        return url, ext


async def download_file(file_id: str, local_path: str) -> str:
    """Baixa arquivo do Telegram para local_path. Retorna path final."""
    url, ext = await get_file_url(file_id)
    final_path = f"{local_path}.{ext}"

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        with open(final_path, "wb") as f:
            f.write(resp.content)

    return final_path
