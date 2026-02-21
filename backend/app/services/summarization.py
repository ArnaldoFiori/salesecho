import asyncio
import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

SUMMARY_PROMPT = """Você é assistente de vendas. Analise a transcrição de uma visita comercial e gere um resumo estruturado.

Vendedor: {seller_name}
Cliente: {customer_name}
Produto: {product}
Transcrição: {transcript}

Gere o resumo com EXATAMENTE estas seções:
- **Contexto**: situação geral da visita (1-2 frases)
- **Necessidades**: o que o cliente precisa ou deseja
- **Produto**: o que foi apresentado/discutido sobre o produto
- **Objeções**: resistências ou preocupações do cliente
- **Próximos passos**: ações combinadas, follow-up

Se alguma seção não se aplica, escreva "Não identificado".
Seja conciso e objetivo. Máximo 300 palavras no total."""


async def summarize_transcript(
    transcript: str, seller_name: str, customer_name: str, product: str
) -> tuple[str, str]:
    """Sumariza transcrição via Groq Llama. Retorna (resumo, modelo)."""
    prompt = SUMMARY_PROMPT.format(
        seller_name=seller_name,
        customer_name=customer_name,
        product=product,
        transcript=transcript,
    )

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    GROQ_URL,
                    headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                    json={
                        "model": MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 1024,
                    },
                )

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 30))
                    await asyncio.sleep(retry_after)
                    continue

                resp.raise_for_status()
                summary = resp.json()["choices"][0]["message"]["content"]
                return summary, MODEL

        except httpx.HTTPStatusError:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt)

    raise RuntimeError("Sumarização falhou após 3 tentativas")
