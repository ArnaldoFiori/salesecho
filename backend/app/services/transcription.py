import asyncio
import os
import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MODEL = "whisper-large-v3-turbo"


async def transcribe_audio(local_path: str) -> tuple[str, str]:
    """Transcreve áudio via Groq Whisper. Retorna (texto, modelo)."""
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                with open(local_path, "rb") as f:
                    resp = await client.post(
                        GROQ_URL,
                        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                        files={"file": (os.path.basename(local_path), f)},
                        data={"model": MODEL, "language": "pt"},
                    )

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 30))
                    logger.warning(f"Groq rate limit, retry in {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status_code == 400:
                    error_body = resp.text
                    logger.error(f"Groq 400 error: {error_body}")
                    raise RuntimeError(f"Groq rejected audio: {error_body[:200]}")
                resp.raise_for_status()
                text = resp.json()["text"]

                word_count = len(text.strip().split())
                if word_count < 10:
                    raise ValueError(
                        f"Transcrição muito curta ({word_count} palavras). "
                        "Não foi possível identificar fala no áudio."
                    )

                return text, MODEL

        except httpx.HTTPStatusError:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt)

    raise RuntimeError("Transcrição falhou após 3 tentativas")
