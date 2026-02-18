# 06 — BUSINESS: CUSTOS OPERACIONAIS E ESCALABILIDADE (v6)

## Status
PENDENTE — aguardando aprovação

## Premissas de Cálculo

| Premissa | MVP | Escala |
|----------|-----|--------|
| Organizações (clientes) | 1-3 | ~10-20 |
| Vendedores totais | 5 | 100 |
| Áudios por vendedor/mês | ~30 | 60 |
| Total áudios/mês | ~150 | 6.000 |
| Duração média do áudio | 3 min (0,05h) | 3 min (0,05h) |
| Horas de áudio/mês | 7,5h | 300h |
| Tokens input por sumarização | ~800 | ~800 |
| Tokens output por sumarização | ~300 | ~300 |

---

## Pricing Atual dos Serviços (fev/2026)

### Groq — Transcrição (Whisper)

| Modelo | Preço | Fonte |
|--------|-------|-------|
| Whisper Large v3 | $0,111/hora | groq.com/pricing |
| **Whisper Large v3 Turbo** (escolhido) | **$0,04/hora** | groq.com/pricing |
| Distil-Whisper (só inglês) | $0,02/hora | groq.com/pricing |

### Groq — Sumarização (LLM)

| Modelo | Input | Output | Fonte |
|--------|-------|--------|-------|
| **Llama 3.3 70B Versatile** (escolhido) | **$0,59/M tokens** | **$0,79/M tokens** | groq.com/pricing |
| Llama 3.1 8B Instant (alternativa barata) | $0,05/M tokens | $0,08/M tokens | groq.com/pricing |

### Supabase

| Plano | Preço | DB | Storage | Bandwidth | MAUs |
|-------|-------|-----|---------|-----------|------|
| Free | $0 | 500MB | 1GB | 5GB | 50K |
| **Pro** | **$25/mês** | 8GB | 100GB | 250GB | 100K |

### Render

| Plano | Preço | RAM | CPU |
|-------|-------|-----|-----|
| **Starter** | **$7/mês** | 512MB | 0.5 vCPU |
| Standard | $25/mês | 2GB | 1 vCPU |

### Frontend Hosting

| Serviço | Preço |
|---------|-------|
| Vercel (free tier) | $0 |
| Cloudflare Pages (free tier) | $0 |

---

## Cenário 1 — MVP (5 vendedores, ~150 áudios/mês)

### Custos Groq

| Item | Cálculo | Custo/mês |
|------|---------|-----------|
| Transcrição Whisper | 150 × 0,05h × $0,04 | **$0,30** |
| Sumarização LLM (input) | 150 × 800 tokens = 120K tokens × $0,59/M | **$0,07** |
| Sumarização LLM (output) | 150 × 300 tokens = 45K tokens × $0,79/M | **$0,04** |
| **Total Groq** | | **$0,41** |

### Custos Infraestrutura

| Serviço | Plano | Custo/mês |
|---------|-------|-----------|
| Supabase | Free | **$0** |
| Render (backend) | Starter | **$7,00** |
| Frontend (Vercel) | Free | **$0** |
| Domínio (.com.br) | Anual ÷ 12 | **~$3,00** |
| **Total Infra** | | **$10,00** |

### Custo Total MVP

| Categoria | Valor/mês |
|-----------|-----------|
| Groq (IA) | $0,41 |
| Infraestrutura | $10,00 |
| **TOTAL** | **$10,41/mês (~R$ 60)** |

### Receita MVP (1 cliente, 5 vendedores)

| Preço por vendedor | Receita mensal | Margem |
|--------------------|----------------|--------|
| R$ 29,90 | R$ 149,50 | **~R$ 90 (60%)** |
| R$ 49,90 | R$ 249,50 | **~R$ 190 (76%)** |
| R$ 79,90 | R$ 399,50 | **~R$ 340 (85%)** |

---

## Cenário 2 — Escala (100 vendedores, 6.000 áudios/mês)

### Custos Groq

| Item | Cálculo | Custo/mês |
|------|---------|-----------|
| Transcrição Whisper | 6.000 × 0,05h × $0,04 | **$12,00** |
| Sumarização LLM (input) | 6.000 × 800 = 4,8M tokens × $0,59/M | **$2,83** |
| Sumarização LLM (output) | 6.000 × 300 = 1,8M tokens × $0,79/M | **$1,42** |
| **Total Groq** | | **$16,25** |

### Custos Infraestrutura

| Serviço | Plano | Justificativa | Custo/mês |
|---------|-------|---------------|-----------|
| Supabase | Pro | DB ~2GB, 100K MAUs ok, 250GB bandwidth ok | **$25,00** |
| Render (backend) | Standard | 6K áudios precisa mais RAM para processamento | **$25,00** |
| Frontend (Vercel) | Free | Ainda cabe no free tier | **$0** |
| Domínio | .com.br | | **~$3,00** |
| **Total Infra** | | | **$53,00** |

### Custo Total Escala

| Categoria | Valor/mês |
|-----------|-----------|
| Groq (IA) | $16,25 |
| Infraestrutura | $53,00 |
| **TOTAL** | **$69,25/mês (~R$ 400)** |

### Receita Escala (100 vendedores, distribuídos em ~10-20 empresas)

| Preço por vendedor | Receita mensal | Custo | Margem |
|--------------------|----------------|-------|--------|
| R$ 29,90 | R$ 2.990 | R$ 400 | **R$ 2.590 (87%)** |
| R$ 49,90 | R$ 4.990 | R$ 400 | **R$ 4.590 (92%)** |
| R$ 79,90 | R$ 7.990 | R$ 400 | **R$ 7.590 (95%)** |

---

## Análise de Volume de Dados (100 vendedores, 6.000 áudios/mês)

### Banco de Dados (Supabase PostgreSQL)

| Tabela | Registros/mês | Tamanho estimado/registro | Total/mês |
|--------|---------------|---------------------------|-----------|
| recordings | 6.000 | ~2KB (textos de transcrição e resumo) | ~12MB |
| customers | ~500 novos | ~200 bytes | ~100KB |
| users | ~10 novos | ~500 bytes | ~5KB |
| organizations | ~2 novos | ~200 bytes | negligível |
| **Total incremental/mês** | | | **~12MB** |

**Projeção anual:** ~144MB. DB total com índices: ~300MB. Cabe no Supabase Free (500MB) no primeiro ano, Pro (8GB) por anos.

### Áudio Temporário (filesystem Render)

| Métrica | Valor |
|---------|-------|
| Áudios simultâneos em processamento | ~5-10 |
| Tamanho médio (3min ogg) | ~500KB |
| Pico simultâneo | ~5MB |
| Storage 24h fallback (pior caso) | ~200 áudios × 500KB = ~100MB |
| Disco disponível Render Starter | 1GB |
| Disco disponível Render Standard | 10GB |

Sem risco de storage.

### Bandwidth (Supabase)

| Operação | Volume/mês |
|----------|-----------|
| Portal reads (20 gestores, ~100 pageviews/dia) | ~2GB |
| API calls (CRUD, filtros, export) | ~1GB |
| **Total** | **~3GB** |

Cabe no Supabase Free (5GB). No Pro (250GB), margem enorme.

---

## Custo por Áudio Processado

| Cenário | Custo Groq/áudio | Custo total/áudio (com infra) |
|---------|-------------------|-------------------------------|
| MVP (150/mês) | $0,0027 (~R$ 0,016) | $0,069 (~R$ 0,40) |
| Escala (6.000/mês) | $0,0027 (~R$ 0,016) | $0,012 (~R$ 0,07) |

O custo de IA por áudio é **fixo e irrelevante** ($0,0027). O custo dominante no MVP é a infraestrutura fixa (Render). Na escala, o custo por áudio cai drasticamente porque a infra fixa se dilui.

---

## Breakeven

### Com preço R$ 29,90/vendedor

| Métrica | Valor |
|---------|-------|
| Custo fixo mensal MVP | ~R$ 60 |
| Receita por vendedor | R$ 29,90 |
| Breakeven | **2 vendedores pagantes** |

### Com preço R$ 49,90/vendedor

| Métrica | Valor |
|---------|-------|
| Custo fixo mensal MVP | ~R$ 60 |
| Receita por vendedor | R$ 49,90 |
| Breakeven | **2 vendedores pagantes** |

O produto é lucrativo a partir do **primeiro cliente com 2+ vendedores**.

---

## Pontos de Inflexão (quando subir de plano)

| Trigger | Ação | Custo adicional |
|---------|------|-----------------|
| DB > 500MB (~3 anos de dados) | Supabase Free → Pro | +$25/mês |
| Backend com lentidão (>50 áudios/hora) | Render Starter → Standard | +$18/mês |
| MAUs > 50K (improvável no curto prazo) | Supabase Free → Pro | +$25/mês |
| >6.000 áudios/mês | Considerar Groq Batch API (50% desconto) | -50% no custo Groq |
| >20.000 áudios/mês | Considerar Llama 3.1 8B em vez de 70B | -90% no custo LLM |

---

## Otimizações Futuras (não MVP)

| Otimização | Economia estimada |
|-----------|-------------------|
| Usar Distil-Whisper ($0,02/h) em vez de Turbo ($0,04/h) | -50% transcrição (se qualidade PT-BR ok) |
| Usar Llama 3.1 8B ($0,05/$0,08) em vez de 70B ($0,59/$0,79) | -90% sumarização (testar qualidade) |
| Groq Batch API para áudios não urgentes | -50% geral |
| Cache de prompts Groq (prompt caching) | -50% input tokens repetidos |
| Supabase: spend cap ativo | Previne surpresas |

---

## Custos Não Recorrentes (setup único)

| Item | Custo | Nota |
|------|-------|------|
| Domínio salesecho.com.br | ~R$ 40/ano | Registro.br |
| Conta Stripe | $0 | Cobra taxa por transação (2,9% + R$ 0,39) |
| Conta Groq | $0 | Pay-as-you-go |
| Conta Supabase | $0 | Free tier |
| Conta Render | $0 | Free tier (mas Starter é $7 para não hibernar) |
| Conta Vercel | $0 | Free tier |
| SSL/HTTPS | $0 | Incluído em todos os serviços |

---

## Taxa Stripe por Transação

| Vendedores | Preço unit. | Valor cobrado | Taxa Stripe (~3,4%) | Líquido |
|-----------|-------------|---------------|---------------------|---------|
| 5 | R$ 29,90 | R$ 149,50 | R$ 5,48 | R$ 144,02 |
| 10 | R$ 29,90 | R$ 299,00 | R$ 10,57 | R$ 288,43 |
| 100 | R$ 29,90 | R$ 2.990,00 | R$ 102,05 | R$ 2.887,95 |

---

## Resumo Executivo

| Métrica | MVP (5 sellers) | Escala (100 sellers) |
|---------|-----------------|---------------------|
| Custo operacional/mês | **~R$ 60** | **~R$ 400** |
| Receita (R$ 29,90/seller) | R$ 149,50 | R$ 2.990 |
| Margem bruta | ~60% | ~87% |
| Custo IA/áudio | R$ 0,016 | R$ 0,016 |
| Breakeven | 2 vendedores | N/A (já lucrativo) |
| Stack sustenta sem mudança até | ~50 sellers | ~500 sellers |
