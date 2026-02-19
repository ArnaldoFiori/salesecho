# 09 — EMAILS TRANSACIONAIS (v6)

## Status
PENDENTE — aguardando aprovação

## Decisões Canônicas

| Decisão | Valor |
|---------|-------|
| Provedor de email | Supabase Auth (confirmação, reset) + Resend ou Supabase Edge Functions (transacionais) |
| Remetente | noreply@salesecho.com.br |
| Reply-to | suporte@salesecho.com.br |
| Formato | HTML responsivo (inline CSS) |
| Alternativa MVP | Supabase Auth para auth emails + cron jobs com SMTP simples para alertas |

---

## Catálogo de Emails

### Emails de Autenticação (Supabase Auth — automáticos)

| # | Trigger | Assunto | Destinatário |
|---|---------|---------|-------------|
| E1 | Signup | "Confirme seu email — SalesEcho" | Gestor |
| E2 | Reset password | "Redefinir sua senha — SalesEcho" | Gestor |
| E3 | Magic link (se habilitado) | "Acesse sua conta — SalesEcho" | Gestor |

Esses emails são configurados no Supabase Dashboard → Auth → Email Templates. Customizar com branding SalesEcho.

### Emails Transacionais do Negócio (backend envia)

| # | Trigger | Assunto | Destinatário | Prioridade |
|---|---------|---------|-------------|------------|
| E4 | Signup confirmado | "Bem-vindo ao SalesEcho!" | Gestor | MVP |
| E5 | Trial expira em 7 dias | "Seu teste expira em 7 dias" | Gestor | MVP |
| E6 | Trial expira em 3 dias | "Seu teste expira em 3 dias" | Gestor | MVP |
| E7 | Trial expira em 1 dia | "Último dia do seu teste" | Gestor | MVP |
| E8 | Trial expirou | "Seu período de teste expirou" | Gestor | MVP |
| E9 | Pagamento confirmado | "Pagamento confirmado — SalesEcho" | Gestor | MVP |
| E10 | Pagamento falhou | "Problema com seu pagamento" | Gestor | MVP |
| E11 | Boleto gerado | "Seu boleto está disponível" | Gestor | MVP |
| E12 | Assinatura cancelada | "Sua assinatura foi cancelada" | Gestor | Pós-MVP |
| E13 | Dados serão excluídos (5d graça) | "Seus dados serão excluídos em 5 dias" | Gestor | MVP |

---

## Templates

### E4 — Bem-vindo ao SalesEcho

**Trigger:** Signup confirmado (email verificado + org criada)

**Assunto:** "Bem-vindo ao SalesEcho! 🎉"

**Corpo:**

```
Olá {gestor_nome},

Sua conta foi criada com sucesso!

Empresa: {org_nome}
Plano: Teste gratuito (30 dias)
Vendedores disponíveis: até 5

Próximos passos:
1. Acesse o portal: https://app.salesecho.com.br
2. Cadastre seus vendedores em "Vendedores → Adicionar"
3. Cada vendedor receberá instruções para usar o bot no Telegram

Dúvidas? Responda este email.

Equipe SalesEcho
```

---

### E5/E6/E7 — Trial expirando

**Trigger:** Cron job diário verifica `subscriptions.trial_ends_at`

**Assunto (E5):** "Seu teste gratuito expira em 7 dias"
**Assunto (E6):** "Seu teste gratuito expira em 3 dias"
**Assunto (E7):** "Último dia do seu teste gratuito"

**Corpo (template, varia dias):**

```
Olá {gestor_nome},

Seu período de teste do SalesEcho expira em {dias} dia(s).

Sua empresa já registrou {total_recordings} visitas de {total_sellers} vendedores.

Para manter o acesso e todos os seus dados, assine agora:
[Assinar] → https://app.salesecho.com.br/account

Aceitamos cartão de crédito, boleto bancário e PIX.

Após a expiração, seus dados serão mantidos por 7 dias.
Depois disso, serão permanentemente excluídos.

Equipe SalesEcho
```

---

### E8 — Trial expirou

**Trigger:** Cron job altera status para `expired`

**Assunto:** "Seu período de teste expirou"

**Corpo:**

```
Olá {gestor_nome},

Seu período de teste do SalesEcho expirou.

Você ainda tem 7 dias para assinar e manter todos os seus dados:
- {total_recordings} visitas registradas
- {total_sellers} vendedores cadastrados
- {total_customers} clientes registrados

[Assinar agora] → https://app.salesecho.com.br/account

Após {data_exclusao}, todos os dados serão permanentemente excluídos.

Equipe SalesEcho
```

---

### E9 — Pagamento confirmado

**Trigger:** Webhook `invoice.payment_succeeded`

**Assunto:** "Pagamento confirmado — SalesEcho"

**Corpo:**

```
Olá {gestor_nome},

Seu pagamento foi confirmado!

Valor: R$ {valor}
Método: {metodo} (cartão/boleto/PIX)
Período: {periodo_inicio} a {periodo_fim}
Vendedores: {seller_count}

Sua fatura está disponível no portal:
https://app.salesecho.com.br/account → Gerenciar Assinatura

Equipe SalesEcho
```

---

### E10 — Pagamento falhou

**Trigger:** Webhook `invoice.payment_failed`

**Assunto:** "⚠️ Problema com seu pagamento — SalesEcho"

**Corpo:**

```
Olá {gestor_nome},

Não conseguimos processar seu pagamento.

Para evitar interrupção do serviço, atualize seu método de pagamento:
[Atualizar pagamento] → https://app.salesecho.com.br/account

Aceitamos cartão de crédito, boleto bancário e PIX.

Se o pagamento não for regularizado em 30 dias, o acesso
será limitado ao modo somente leitura e, após esse período, bloqueado.

Equipe SalesEcho
```

---

### E11 — Boleto gerado

**Trigger:** Webhook `payment_intent.requires_action` (boleto)

**Assunto:** "Seu boleto SalesEcho está disponível"

**Corpo:**

```
Olá {gestor_nome},

Seu boleto para pagamento do SalesEcho foi gerado.

Valor: R$ {valor}
Vencimento: {data_vencimento} (5 dias)
Código de barras: {codigo_barras}

[Visualizar boleto] → {boleto_url}

Após o pagamento, a confirmação pode levar até 3 dias úteis.
Se preferir acesso imediato, pague via PIX ou cartão no portal.

Equipe SalesEcho
```

---

### E13 — Dados serão excluídos

**Trigger:** Cron job, 2 dias antes da exclusão (trial expirado + 5 dias)

**Assunto:** "⚠️ Seus dados serão excluídos em 2 dias"

**Corpo:**

```
Olá {gestor_nome},

ATENÇÃO: os dados da sua empresa no SalesEcho serão
permanentemente excluídos em {data_exclusao}.

Isso inclui:
- {total_recordings} visitas registradas
- {total_sellers} vendedores cadastrados
- Todas as transcrições e resumos

Esta ação é irreversível.

Para preservar seus dados, assine agora:
[Assinar] → https://app.salesecho.com.br/account

Equipe SalesEcho
```

---

## Implementação — Envio de Emails

### Opção A — Resend (recomendada, simples)

```python
import httpx

async def send_email(to: str, subject: str, html: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": "SalesEcho <noreply@salesecho.com.br>",
                "to": to,
                "subject": subject,
                "html": html,
                "reply_to": "suporte@salesecho.com.br"
            }
        )
```

**Custo Resend:** Free tier = 100 emails/dia, 3.000/mês. Suficiente para MVP.

### Opção B — SMTP direto (fallback)

Usar provedor SMTP (Gmail workspace, Zoho, etc.) via `aiosmtplib`.

---

## Cron Jobs para Emails

| Job | Frequência | Query | Email |
|-----|-----------|-------|-------|
| Trial expira 7d | Diário 09:00 BRT | `WHERE status='trial' AND trial_ends_at BETWEEN now()+6d AND now()+7d` | E5 |
| Trial expira 3d | Diário 09:00 BRT | `WHERE status='trial' AND trial_ends_at BETWEEN now()+2d AND now()+3d` | E6 |
| Trial expira 1d | Diário 09:00 BRT | `WHERE status='trial' AND trial_ends_at BETWEEN now() AND now()+1d` | E7 |
| Trial expirou | Diário 00:00 UTC | `WHERE status='trial' AND trial_ends_at < now()` | E8 |
| Dados excluídos 2d | Diário 09:00 BRT | `WHERE status='expired' AND trial_ends_at < now()-5d` | E13 |

---

## Env Vars Adicionais

| Variável | Descrição |
|----------|-----------|
| `RESEND_API_KEY` | API key do Resend (re_...) |
| `EMAIL_FROM` | `SalesEcho <noreply@salesecho.com.br>` |
| `EMAIL_REPLY_TO` | `suporte@salesecho.com.br` |

---

## DNS para Email

| Registro | Tipo | Valor | Finalidade |
|----------|------|-------|-----------|
| Resend verification | TXT | Conforme Resend Dashboard | Verificar domínio |
| SPF | TXT | `v=spf1 include:resend.com ~all` | Anti-spam |
| DKIM | CNAME | Conforme Resend Dashboard | Autenticação |
| DMARC | TXT | `v=DMARC1; p=none; rua=mailto:dmarc@salesecho.com.br` | Monitoramento |
