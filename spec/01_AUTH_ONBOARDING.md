# 01 — AUTH & ONBOARDING (v6)

## Status
APROVADO (v2: correções Spec 12)

## Decisões Canônicas

| Decisão | Valor |
|---------|-------|
| Mecanismo auth | Supabase Auth nativo (email+senha) |
| Forgot password | Supabase Auth built-in (email) |
| Token | JWT emitido pelo Supabase Auth |
| JWT lifetime | Access token: 1 hora / Refresh token: 7 dias (default Supabase) |
| Multi-tenancy | RLS por `org_id` no Supabase |
| Gateway pagamento | Stripe (recorrente mensal) |
| Unidade cobrança | Vendedor cadastrado (ativo ou não) |
| Org admins por org | **1 (único) no MVP** |

---

## Roles

| Role | Acesso | Criação | Login portal |
|------|--------|---------|--------------|
| system_admin | Qualquer org (auditado) | Manual no Supabase | Sim |
| org_admin | Somente própria org | Auto-cadastro em salesecho.com.br | Sim |
| seller | Somente Telegram | Cadastrado pelo org_admin | Não |

**Restrição MVP:** cada organização tem exatamente 1 org_admin. Não há endpoint para convidar gestores adicionais. Se necessário, trocar o gestor exige intervenção do system_admin.

---

## Fluxo 1 — Cadastro Empresa (org_admin)

### Passo a passo

1. Gestor acessa `www.salesecho.com.br`
2. Clica "Criar conta" → formulário:

| Campo | Tipo | Validação |
|-------|------|-----------|
| Nome completo | text | obrigatório, min 3 chars |
| Cargo | text | obrigatório |
| Email corporativo | email | obrigatório, domínios pessoais bloqueados |
| Nome da empresa | text | obrigatório |
| Nº estimado de vendedores | number | obrigatório, min 1 |
| Senha | password | min 8 chars |
| Confirmar senha | password | deve coincidir |
| Checkbox: aceite de termos | boolean | obrigatório |

### Blocklist de Domínios de Email

Validação no frontend (antes do submit) e no backend (trigger de signup):

```
gmail.com, googlemail.com, hotmail.com, outlook.com, live.com, msn.com,
yahoo.com, yahoo.com.br, bol.com.br, uol.com.br, icloud.com, me.com,
protonmail.com, proton.me, aol.com, zoho.com, gmx.com, gmx.de,
terra.com.br, ig.com.br
```

**Mensagem de rejeição:** "Use um email corporativo. Domínios pessoais como gmail.com e hotmail.com não são aceitos."

3. Frontend chama Supabase Auth `signUp(email, password, { data: {...} })`
4. Backend (trigger `on_auth_user_created`) cria:
   - Registro em `organizations` (name, estimated_sellers)
   - Registro em `users` (role=org_admin, org_id=nova org)
   - Registro em `subscriptions` (status=trial, trial_ends_at=now+30d, seller_limit=5)
5. Supabase Auth envia email de confirmação
6. Gestor confirma email → acesso liberado
7. Aviso **obrigatório** exibido no cadastro:

> "Durante o período de teste (30 dias), você pode cadastrar até 5 vendedores gratuitamente. Ao final do período, caso não assine um plano, sua conta e todos os dados serão permanentemente excluídos."

---

## Fluxo 2 — Login

1. Gestor acessa portal → tela de login
2. Email + senha → `supabase.auth.signInWithPassword({ email, password })`
3. JWT retornado com `user_id`
4. Backend resolve `org_id` via tabela `users`
5. Toda query filtrada por `org_id` (RLS)

### JWT e Refresh Token

| Parâmetro | Valor | Config |
|-----------|-------|--------|
| Access token TTL | 1 hora (3600s) | Supabase Dashboard → Auth → JWT Settings |
| Refresh token TTL | 7 dias | Supabase default |
| Refresh automático | Sim | `supabase.auth.onAuthStateChange()` no frontend |

Frontend usa `onAuthStateChange` para renovar automaticamente antes da expiração. Sem ação manual do usuário.

---

## Fluxo 3 — Forgot Password

1. Gestor clica "Esqueci minha senha"
2. Informa email
3. `supabase.auth.resetPasswordForEmail(email)`
4. Sempre exibe: "Se este email estiver cadastrado, você receberá um link" (não revela se existe)
5. Gestor define nova senha
6. Redirecionado para login

---

## Fluxo 4 — Trial

| Regra | Valor |
|-------|-------|
| Duração | 30 dias |
| Cartão exigido | Não |
| Limite vendedores | 5 |
| Expiração sem pagamento | Acesso bloqueado + dados deletados (7 dias de graça) |
| Aviso no cadastro | Obrigatório (texto explícito) |

## Assinatura (pós-trial)

| Regra | Valor |
|-------|-------|
| Gateway | Stripe |
| Modelo | Recorrente mensal |
| Unidade de cobrança | Vendedor cadastrado (ativo ou não) |
| Métodos de pagamento | Cartão, boleto, PIX |
| Inadimplência ≤30d | Acesso restrito (read-only), dados preservados |
| Inadimplência >30d | Acesso bloqueado, dados preservados |

## Diferença Trial vs. Inadimplência

| Cenário | Acesso | Dados |
|---------|--------|-------|
| Trial expirado sem pagamento | Bloqueado | **Deletados** (após 7d de graça) |
| Assinante inadimplente ≤30d | Restrito (read-only) | Preservados |
| Assinante inadimplente >30d | Bloqueado | Preservados |

---

## Fluxo 5 — Cadastro de Vendedores (pelo org_admin)

1. Org_admin acessa portal → seção "Vendedores"
2. Cadastra:
   - Nome completo (obrigatório, min 3 chars)
   - Número de celular (obrigatório, formato BR com máscara)
3. Backend normaliza telefone (ver `normalize_phone()` abaixo)
4. Verifica limite de vendedores (`seller_count < seller_limit`)
5. Cria registro em `users` (role=seller, org_id, phone, phone_normalized)
6. Vendedor **não** tem login no portal

---

## Fluxo 6 — Vinculação Seller ↔ Telegram

1. Vendedor envia primeira mensagem ao bot do Telegram
2. Bot pede para compartilhar contato (botão `request_contact`)
3. Bot extrai `phone_number` do contato compartilhado
4. Backend normaliza e busca `users.phone_normalized`
5. Se encontrou match:
   - Grava `telegram_chat_id` no registro do seller
   - Bot responde com mensagem de boas-vindas + instruções + aviso LGPD
6. Se **não** encontrou:
   - Bot responde: "Número não cadastrado. Peça ao seu gestor para cadastrá-lo no portal SalesEcho."

### normalize_phone()

```python
import re

def normalize_phone(phone: str) -> str:
    """
    Normaliza telefone para formato: somente dígitos com DDI Brasil.
    Resultado: '5511999998888'

    Aceita:
    - +55 (11) 99999-8888
    - 055 11 99999 8888
    - 5511999998888
    - 11999998888
    - (11) 99999-8888
    """
    digits = re.sub(r'\D', '', phone)           # Remove tudo que não é dígito
    if digits.startswith('0'):
        digits = digits[1:]                      # Remove zero à esquerda (0xx)
    if not digits.startswith('55'):
        digits = '55' + digits                   # Adiciona DDI se ausente
    return digits
```

---

## Fluxo 7 — System Admin

| Ação | Como |
|------|------|
| Criar system_admin | INSERT manual na tabela `users` + Supabase Auth |
| Acesso | Login normal no portal |
| Diferencial | Vê todas as orgs, com filtro por org_id |
| Auditoria | Toda ação logada em `support_audit` (user_id, org_id, action, timestamp) |
| Limite | Somente leitura — não edita dados de negócio |

---

## Contratos API — Auth

### POST /auth/signup (via Supabase Auth SDK — frontend direto)

Request:
```json
{
  "email": "gestor@empresa.com.br",
  "password": "********",
  "options": {
    "data": {
      "full_name": "João Silva",
      "job_title": "Diretor Comercial",
      "company_name": "Empresa ABC",
      "estimated_sellers": 15
    }
  }
}
```

Response: Supabase Auth padrão (user object + JWT)

Trigger (database function `handle_new_user_signup`): cria org + user + subscription automaticamente.

### POST /auth/login (via Supabase Auth SDK — frontend direto)

```javascript
const { data, error } = await supabase.auth.signInWithPassword({
    email: 'gestor@empresa.com.br',
    password: '********'
})
// data.session.access_token → JWT para requests ao backend
```

### Chamadas ao backend (todas as rotas protegidas)

```
Authorization: Bearer <jwt>
```

Backend decodifica JWT usando `SUPABASE_JWT_SECRET`, extrai `sub` (user_id), busca `org_id` e `role` via tabela `users`.
