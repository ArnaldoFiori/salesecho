# 11 — LANDING PAGE (v6)

## Status
PENDENTE — aguardando aprovação

## Decisões Canônicas

| Decisão | Valor |
|---------|-------|
| URL | www.salesecho.com.br |
| Hosting | Vercel free tier (mesmo projeto frontend, rota separada) ou página separada |
| Framework | React (mesmo stack) ou HTML estático |
| Responsividade | Mobile-first |
| CTA principal | "Teste grátis por 30 dias" → redirect `/signup` |
| Idioma | Português BR |
| Analytics | Google Analytics 4 (ou Plausible free) |

---

## Público-Alvo

| Persona | Cargo | Dor |
|---------|-------|-----|
| Gestor comercial | Diretor/Gerente de vendas | Não sabe o que acontece nas visitas dos vendedores |
| Dono de empresa (PME) | Sócio/CEO | Equipe externa sem controle, relatórios manuais |
| Coordenador de equipe | Coordenador/Supervisor | Perde tempo cobrando relatórios escritos |

---

## Estrutura de Seções

### 1. Hero (acima da dobra)

| Elemento | Conteúdo |
|----------|---------|
| Headline | "Saiba o que acontece em cada visita da sua equipe comercial" |
| Sub-headline | "Seus vendedores gravam um áudio no Telegram. A IA transcreve e gera relatórios automaticamente." |
| CTA primário | Botão "Teste grátis por 30 dias" → `/signup` |
| CTA secundário | Link "Veja como funciona" → scroll para seção "Como funciona" |
| Visual | Mockup do portal com dashboard ou ilustração de vendedor + celular |

---

### 2. Problema

| Elemento | Conteúdo |
|----------|---------|
| Headline | "O problema que todo gestor comercial conhece" |
| Pain point 1 | "Vendedores visitam clientes mas você não sabe o que conversaram" |
| Pain point 2 | "Relatórios escritos são vagos, atrasados ou nunca chegam" |
| Pain point 3 | "Sem visibilidade, você não consegue ajudar sua equipe a vender mais" |

---

### 3. Como Funciona (3 passos)

| Passo | Ícone | Título | Descrição |
|-------|-------|--------|-----------|
| 1 | 🎙️ | Vendedor grava um áudio | Após a visita, ele envia um áudio de até 10 min pelo Telegram. Sem app extra, sem formulário. |
| 2 | 🤖 | IA transcreve e resume | Em segundos, o áudio vira texto com os pontos-chave: necessidades do cliente, objeções, próximos passos. |
| 3 | 📊 | Gestor acompanha tudo | Pelo portal web, você vê todas as visitas da equipe, filtra por vendedor, cliente e período. |

---

### 4. Benefícios

| Benefício | Para quem | Descrição |
|-----------|-----------|-----------|
| Zero fricção para o vendedor | Vendedor | Não precisa instalar app, não precisa escrever. Só falar. |
| Visibilidade total | Gestor | Saiba o que cada vendedor conversou, com cada cliente, todo dia. |
| Decisões com dados | Gestor | Identifique padrões, objeções recorrentes e oportunidades perdidas. |
| Setup em 5 minutos | Gestor | Crie a conta, cadastre os vendedores, pronto. |

---

### 5. Prova Social / Números (quando houver)

MVP: usar métricas do produto em vez de depoimentos.

| Métrica | Valor (placeholder) |
|---------|---------------------|
| Áudios processados | "Milhares de visitas registradas" |
| Tempo economizado | "Vendedores gastam 30 segundos em vez de 15 minutos escrevendo" |
| Precisão | "Transcrição por IA de última geração" |

Pós-MVP: substituir por depoimentos reais de clientes.

---

### 6. Preço

| Elemento | Conteúdo |
|----------|---------|
| Headline | "Simples e transparente" |
| Modelo | "R$ X,XX por vendedor/mês" |
| Destaque | "Teste grátis por 30 dias — sem cartão de crédito" |
| Inclui | "Portal web, bot Telegram, transcrição IA, resumos automáticos, exportação Excel" |
| Métodos | "Cartão, boleto ou PIX" |
| CTA | Botão "Começar teste grátis" → `/signup` |

---

### 7. FAQ

| Pergunta | Resposta |
|----------|---------|
| Precisa instalar algum app? | Não. O vendedor usa o Telegram que já tem no celular. |
| O áudio fica armazenado? | Não. O áudio original é automaticamente excluído em 24 horas. Apenas a transcrição e o resumo ficam salvos. |
| Funciona com qualquer idioma? | O foco é português brasileiro, mas a IA suporta outros idiomas. |
| Quantos vendedores posso cadastrar? | No teste gratuito, até 5. Após assinar, sem limite. |
| E se o vendedor não tiver Telegram? | Telegram é gratuito e leva 2 minutos para instalar. É o app de mensagens mais usado no Brasil depois do WhatsApp. |
| Posso cancelar a qualquer momento? | Sim, sem multa. Seus dados ficam preservados. |
| É seguro? | Sim. Dados isolados por empresa, criptografia em trânsito e repouso, conformidade com LGPD. |
| Quanto tempo leva o processamento? | Normalmente menos de 30 segundos entre o envio do áudio e o resumo pronto. |

---

### 8. CTA Final

| Elemento | Conteúdo |
|----------|---------|
| Headline | "Comece a ter visibilidade sobre sua equipe comercial hoje" |
| CTA | Botão grande "Criar conta gratuita" → `/signup` |
| Reforço | "30 dias grátis. Sem cartão. Setup em 5 minutos." |

---

### 9. Footer

| Elemento | Link |
|----------|------|
| Termos de Uso | `/termos` |
| Política de Privacidade | `/privacidade` |
| Contato | suporte@salesecho.com.br |
| © 2026 SalesEcho | — |

---

## SEO

| Meta | Valor |
|------|-------|
| Title | "SalesEcho — Relatórios de visita comercial por voz e IA" |
| Description | "Seus vendedores gravam um áudio no Telegram. A IA transcreve e gera relatórios automaticamente. Teste grátis por 30 dias." |
| Keywords | relatório de visita, gestão equipe comercial, vendedor externo, transcrição áudio, IA vendas |
| OG Image | Card social com logo + headline |
| Canonical | `https://www.salesecho.com.br` |

---

## Analytics

| Evento | Trigger |
|--------|---------|
| `page_view` | Carregou landing page |
| `cta_hero_click` | Clicou CTA do hero |
| `cta_pricing_click` | Clicou CTA da seção preço |
| `cta_footer_click` | Clicou CTA final |
| `faq_expand` | Expandiu pergunta do FAQ |
| `signup_redirect` | Redirecionou para `/signup` |

---

## Responsividade

| Breakpoint | Layout |
|-----------|--------|
| < 768px (mobile) | Single column, CTAs full-width, hero image abaixo do texto |
| 768-1024px (tablet) | 2 colunas onde aplicável |
| > 1024px (desktop) | Layout completo, hero com imagem lateral |

---

## Tom de Voz

| Atributo | Diretriz |
|----------|---------|
| Tom | Direto, prático, confiável |
| Evitar | Jargão técnico, termos em inglês desnecessários, hype |
| Priorizar | Resultado concreto, facilidade, economia de tempo |
| Pessoa | "Você" (gestor), "seus vendedores", "sua equipe" |
