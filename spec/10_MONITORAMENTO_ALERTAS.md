# 10 — MONITORAMENTO & ALERTAS (v6)

## Status
PENDENTE — aguardando aprovação

## Decisões Canônicas

| Decisão | Valor |
|---------|-------|
| Abordagem MVP | Logging estruturado + health checks + alertas por Telegram |
| APM/Dashboard | Não no MVP (Render metrics + Supabase dashboard são suficientes) |
| Log format | JSON estruturado (stdout) |
| Canal de alerta | Bot Telegram para system_admin |
| Métricas externas | Render metrics (free), Supabase dashboard (free) |
| Uptime monitoring | UptimeRobot free tier (5 monitores, checks 5min) |

---

## Health Checks

### Backend — GET /health

```python
@app.get("/health")
async def health():
    """Health check básico. Render usa para auto-restart."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health/deep")
async def health_deep():
    """Health check profundo. Verifica dependências."""
    checks = {}

    # Database
    try:
        await db.fetchval("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Groq API
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"}
            )
            checks["groq"] = "ok" if resp.status_code == 200 else f"error: {resp.status_code}"
    except Exception as e:
        checks["groq"] = f"error: {str(e)}"

    # Stripe
    try:
        stripe.Account.retrieve()
        checks["stripe"] = "ok"
    except Exception as e:
        checks["stripe"] = f"error: {str(e)}"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
```

### Render — configuração

```yaml
# render.yaml
healthCheckPath: /health
```

Render reinicia automaticamente se `/health` retornar erro por 5 minutos consecutivos.

### UptimeRobot — monitores

| Monitor | URL | Intervalo | Alerta |
|---------|-----|-----------|--------|
| Backend API | `https://api.salesecho.com.br/health` | 5 min | Email + Telegram |
| Frontend | `https://app.salesecho.com.br` | 5 min | Email + Telegram |
| Supabase | `https://xxxx.supabase.co/rest/v1/` | 5 min | Email |

---

## Logging Estruturado

### Formato

Todos os logs em JSON para stdout (Render captura automaticamente).

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if hasattr(record, "extra"):
            log.update(record.extra)
        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)
        return json.dumps(log)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("salesecho")
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

### Eventos logados

| Evento | Nível | Campos extras |
|--------|-------|--------------|
| Áudio recebido | INFO | `org_id`, `seller_id`, `telegram_message_id` |
| Transcrição completa | INFO | `recording_id`, `duration_sec`, `model` |
| Sumarização completa | INFO | `recording_id`, `model` |
| Recording salvo | INFO | `recording_id`, `status` |
| Transcrição falhou | ERROR | `recording_id`, `error`, `attempt` |
| Sumarização falhou | ERROR | `recording_id`, `error`, `attempt` |
| Groq rate limit (429) | WARNING | `recording_id`, `retry_after` |
| Webhook Telegram recebido | DEBUG | `update_id`, `chat_id` |
| Webhook Stripe recebido | INFO | `event_type`, `event_id` |
| Stripe payment failed | WARNING | `subscription_id`, `org_id` |
| Seller não encontrado | WARNING | `chat_id` |
| Dedup detectado | INFO | `seller_id`, `telegram_message_id` |
| Auth falhou | WARNING | `ip`, `email` |
| Health check deep | INFO | `checks` |

---

## Alertas — Bot Telegram para Admin

### Conceito

Reutilizar o mesmo bot Telegram (ou criar um segundo) para enviar alertas ao system_admin. Mensagens enviadas para um chat_id fixo do admin.

### Configuração

| Env var | Descrição |
|---------|-----------|
| `ADMIN_TELEGRAM_CHAT_ID` | Chat ID do system_admin para alertas |
| `ALERT_ENABLED` | `true` / `false` |

### Eventos que geram alerta

| Evento | Severidade | Mensagem |
|--------|-----------|----------|
| Pipeline error rate >10% (últimos 30 min) | 🔴 CRÍTICO | "Pipeline: {X}% de erros nas últimas 30min ({N} falhas de {total})" |
| Groq API indisponível (3 falhas consecutivas) | 🔴 CRÍTICO | "Groq API fora: {N} falhas consecutivas. Último erro: {err}" |
| Stripe webhook falhou | 🟡 ATENÇÃO | "Stripe webhook error: {event_type} — {err}" |
| Health check deep degradado | 🟡 ATENÇÃO | "Health degraded: {checks}" |
| Novo signup | 🟢 INFO | "Novo cliente: {org_name} ({email})" |
| Trial expirando (0 dias) | 🟢 INFO | "Trial expirou: {org_name}" |
| Pagamento confirmado | 🟢 INFO | "Pagamento: {org_name} — R$ {valor}" |

### Implementação

```python
async def send_admin_alert(message: str, severity: str = "info"):
    if not ALERT_ENABLED:
        return
    emoji = {"critical": "🔴", "warning": "🟡", "info": "🟢"}.get(severity, "ℹ️")
    text = f"{emoji} SalesEcho Alert\n\n{message}\n\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": ADMIN_TELEGRAM_CHAT_ID, "text": text}
            )
    except Exception:
        logger.error("Failed to send admin alert", exc_info=True)
```

---

## Métricas de Pipeline — Contadores em Memória

### Conceito

Contadores simples em memória para calcular taxa de erro. Reset a cada 30 minutos.

```python
from collections import defaultdict
import time

class PipelineMetrics:
    def __init__(self, window_seconds=1800):  # 30 min
        self.window = window_seconds
        self.events = []

    def record(self, success: bool):
        now = time.time()
        self.events.append((now, success))
        # Limpar eventos fora da janela
        self.events = [(t, s) for t, s in self.events if now - t < self.window]

    @property
    def error_rate(self) -> float:
        if not self.events:
            return 0.0
        failures = sum(1 for _, s in self.events if not s)
        return failures / len(self.events)

    @property
    def total(self) -> int:
        return len(self.events)

    @property
    def failures(self) -> int:
        return sum(1 for _, s in self.events if not s)

pipeline_metrics = PipelineMetrics()
```

### Check periódico (a cada 5 min)

```python
async def check_pipeline_health():
    """Executado por scheduler (APScheduler ou asyncio loop)."""
    if pipeline_metrics.total >= 5 and pipeline_metrics.error_rate > 0.10:
        await send_admin_alert(
            f"Pipeline: {pipeline_metrics.error_rate:.0%} de erros "
            f"nas últimas 30min ({pipeline_metrics.failures} falhas "
            f"de {pipeline_metrics.total})",
            severity="critical"
        )
```

---

## Dashboard Operacional — GET /api/admin/metrics (system_admin)

```python
@app.get("/api/admin/metrics")
async def admin_metrics(user = Depends(require_system_admin)):
    """Métricas operacionais para system_admin."""
    return {
        "pipeline": {
            "total_30min": pipeline_metrics.total,
            "failures_30min": pipeline_metrics.failures,
            "error_rate_30min": pipeline_metrics.error_rate,
        },
        "recordings_today": await db.fetchval(
            "SELECT COUNT(*) FROM recordings WHERE created_at > CURRENT_DATE"
        ),
        "recordings_pending": await db.fetchval(
            "SELECT COUNT(*) FROM recordings WHERE status IN ('received', 'transcribing')"
        ),
        "recordings_error_today": await db.fetchval(
            "SELECT COUNT(*) FROM recordings WHERE status = 'error' AND created_at > CURRENT_DATE"
        ),
        "orgs_active": await db.fetchval(
            "SELECT COUNT(*) FROM subscriptions WHERE status IN ('trial', 'active')"
        ),
        "orgs_past_due": await db.fetchval(
            "SELECT COUNT(*) FROM subscriptions WHERE status = 'past_due'"
        ),
    }
```

Exibido na tela `/admin/orgs` (Spec 04) como cards no topo.

---

## Render Metrics (gratuito)

Disponível no Render Dashboard para o serviço:

- CPU usage
- Memory usage
- Request count
- Response time (p50, p95, p99)
- HTTP status codes

Sem configuração adicional.

---

## Supabase Dashboard (gratuito)

Disponível no Supabase Dashboard:

- Database size
- Active connections
- API requests/sec
- Auth users count
- Bandwidth usage

---

## Evolução Pós-MVP

| Evolução | Quando | Ferramenta |
|----------|--------|-----------|
| APM (tracing, métricas detalhadas) | >50 clientes | Sentry free tier ou Grafana Cloud free |
| Log aggregation | >50 clientes | Render log streams → Better Stack / Logtail |
| Alertas por email (além de Telegram) | >10 clientes | Resend (já configurado em Spec 09) |
| Status page pública | >20 clientes | Instatus free ou Cachet |
| Error tracking frontend | >10 clientes | Sentry JS free tier |
