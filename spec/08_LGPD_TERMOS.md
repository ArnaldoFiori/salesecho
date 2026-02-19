# 08 — LGPD & TERMOS DE USO (v6)

## Status
PENDENTE — aguardando aprovação

## Decisões Canônicas

| Decisão | Valor |
|---------|-------|
| Legislação aplicável | LGPD (Lei 13.709/2018) |
| Controlador dos dados | Organização cliente (empresa que contrata SalesEcho) |
| Operador dos dados | SalesEcho (processa dados a pedido do controlador) |
| DPO (Encarregado) | Não obrigatório para MVP (micro/pequena empresa), mas definir email de contato |
| Base legal — gestor | Consentimento (aceite dos termos no signup) |
| Base legal — vendedor | Legítimo interesse do empregador + ciência do vendedor |
| Hospedagem dos dados | Supabase (AWS us-east-1) — fora do Brasil |

---

## Documentos Necessários

| Documento | URL | Obrigatório no MVP |
|-----------|-----|---------------------|
| Termos de Uso | app.salesecho.com.br/termos | Sim |
| Política de Privacidade | app.salesecho.com.br/privacidade | Sim |
| Acordo de Processamento de Dados (DPA) | Disponível sob demanda | Não no MVP |

---

## Termos de Uso — Estrutura

### 1. Definições

| Termo | Definição |
|-------|-----------|
| Plataforma | SalesEcho, incluindo portal web e bot Telegram |
| Gestor | Usuário org_admin que contratou o serviço |
| Vendedor | Colaborador da organização que envia áudios via Telegram |
| Organização | Empresa cliente que contratou SalesEcho |
| Dados de Visita | Áudios, transcrições e resumos gerados pelo uso |

### 2. Aceitação

- Checkbox obrigatório no signup: "Li e aceito os Termos de Uso e a Política de Privacidade"
- Links clicáveis para ambos os documentos
- Sem aceite → cadastro bloqueado

### 3. Descrição do Serviço

- SalesEcho é plataforma de registro e análise de visitas comerciais
- Vendedores enviam áudios via Telegram
- Áudios são transcritos e resumidos por inteligência artificial
- Gestores acessam relatórios pelo portal web

### 4. Responsabilidades do Gestor

- Garantir que vendedores estejam cientes do uso da ferramenta
- Obter consentimento dos vendedores conforme legislação trabalhista
- Manter dados de cadastro atualizados
- Não utilizar a plataforma para fins ilegais
- Responsável pelo pagamento da assinatura

### 5. Responsabilidades do SalesEcho

- Manter a plataforma disponível (sem SLA no MVP)
- Processar dados conforme esta política
- Não vender ou compartilhar dados com terceiros para fins de marketing
- Notificar sobre incidentes de segurança

### 6. Uso Aceitável

- Proibido enviar conteúdo ilegal, ofensivo ou discriminatório
- Proibido tentar acessar dados de outras organizações
- Proibido utilizar a API para fins não autorizados

### 7. Propriedade Intelectual

- Dados de visita pertencem à Organização
- Software e marca pertencem ao SalesEcho
- Transcrições e resumos gerados por IA são de uso da Organização

### 8. Pagamento e Cancelamento

- Conforme Spec 05: trial 30 dias, cobrança por vendedor/mês
- Cancelamento via portal Stripe ou solicitação por email
- Dados preservados após cancelamento (não deletados automaticamente)
- Trial expirado: dados deletados após 7 dias de graça

### 9. Limitação de Responsabilidade

- SalesEcho não garante 100% de acurácia nas transcrições e resumos
- IA pode cometer erros — gestores devem validar informações críticas
- SalesEcho não se responsabiliza por decisões tomadas com base nos resumos

### 10. Modificações dos Termos

- SalesEcho pode alterar os termos com 30 dias de antecedência
- Notificação por email ao gestor
- Uso continuado após notificação implica aceite

### 11. Rescisão

- SalesEcho pode encerrar conta por violação dos termos
- Gestor pode solicitar exclusão completa dos dados a qualquer momento

### 12. Foro

- Comarca de [cidade da empresa] — Brasil
- Lei brasileira aplicável

---

## Política de Privacidade — Estrutura

### 1. Dados Coletados

| Dado | Titular | Finalidade | Base Legal |
|------|---------|-----------|------------|
| Nome, email, cargo | Gestor | Cadastro e autenticação | Consentimento |
| Nome da empresa | Gestor | Identificação da org | Consentimento |
| Nome, telefone | Vendedor | Cadastro e vinculação Telegram | Legítimo interesse |
| telegram_chat_id | Vendedor | Identificação no Telegram | Legítimo interesse |
| Áudios de visitas | Vendedor | Transcrição e análise | Legítimo interesse |
| Transcrições | Derivado | Registro da visita | Legítimo interesse |
| Resumos IA | Derivado | Relatório ao gestor | Legítimo interesse |
| Nome de clientes/prospects | Vendedor (input) | Organização dos registros | Legítimo interesse |
| Dados de pagamento | Gestor | Cobrança | Execução de contrato |
| IP, user agent | Gestor | Segurança e logs | Legítimo interesse |

### 2. Como os Dados São Processados

| Etapa | Processamento | Retenção |
|-------|--------------|----------|
| Áudio recebido | Download do Telegram, salvo temporariamente | **24 horas** (deletado automaticamente) |
| Transcrição | Enviado para Groq Whisper API | Texto salvo no banco |
| Sumarização | Enviado para Groq Llama API | Texto salvo no banco |
| Dados de cadastro | Armazenados no Supabase | Até exclusão da conta |
| Dados de pagamento | Processados pelo Stripe | Conforme política Stripe |

### 3. Compartilhamento com Terceiros

| Terceiro | Dados Compartilhados | Finalidade |
|----------|---------------------|-----------|
| Groq (API) | Áudio (transcrição), texto (sumarização) | Processamento de IA |
| Stripe | Email, nome (gestor) | Pagamentos |
| Supabase | Todos os dados do banco | Hospedagem |
| Telegram | telegram_chat_id, mensagens do bot | Canal de comunicação |

**Nenhum dado é vendido ou compartilhado para fins de marketing.**

### 4. Transferência Internacional

- Dados armazenados no Supabase (AWS us-east-1, EUA)
- Groq processa dados nos EUA
- Stripe processa dados nos EUA
- Base legal: cláusulas contratuais padrão e consentimento do titular

### 5. Direitos do Titular (LGPD Art. 18)

| Direito | Como Exercer |
|---------|-------------|
| Confirmação de tratamento | Email para privacidade@salesecho.com.br |
| Acesso aos dados | Export via portal (gestor) ou email |
| Correção | Portal (gestor) ou email |
| Eliminação | Solicitação por email — executado em até 15 dias |
| Portabilidade | Export XLSX via portal |
| Revogação do consentimento | Email ou cancelamento da conta |
| Oposição ao tratamento | Email — avaliado caso a caso |

### 6. Retenção de Dados

| Tipo | Retenção |
|------|----------|
| Áudio original | 24 horas |
| Transcrições e resumos | Enquanto conta ativa |
| Dados de cadastro | Enquanto conta ativa |
| Após cancelamento | Preservados até solicitação de exclusão |
| Trial expirado sem assinatura | Deletados 7 dias após expiração |
| Logs de acesso (support_audit) | 1 ano |

### 7. Segurança

| Medida | Implementação |
|--------|--------------|
| Criptografia em trânsito | HTTPS/TLS em todas as comunicações |
| Criptografia em repouso | Supabase (AES-256 no AWS) |
| Isolamento de dados | RLS por org_id (multi-tenancy) |
| Autenticação | Supabase Auth com JWT |
| Senhas | Hash bcrypt (Supabase padrão) |
| Acesso admin | Auditado em support_audit |

### 8. Incidentes de Segurança

- SalesEcho notificará gestores afetados em até 72 horas
- Comunicação à ANPD quando necessário (conforme LGPD Art. 48)
- Canal: email cadastrado + banner no portal

### 9. Contato

| Canal | Valor |
|-------|-------|
| Email privacidade | privacidade@salesecho.com.br |
| Email suporte | suporte@salesecho.com.br |

---

## Implementação no Produto

### Signup (Spec 01/04)

Checkbox obrigatório antes do botão "Criar conta":

```
☐ Li e aceito os [Termos de Uso] e a [Política de Privacidade]
```

Links abrem em nova aba. Sem check → botão desabilitado.

### Bot Telegram (primeiro contato com vendedor)

Mensagem de vinculação inclui aviso:

```
✅ Olá {nome}! Você está vinculado à empresa {org}.

ℹ️ Seus áudios serão transcritos e resumidos por IA para
relatórios da sua empresa. Os áudios originais são deletados
em até 24 horas. Em caso de dúvidas, fale com seu gestor.
```

### Páginas estáticas

| URL | Conteúdo |
|-----|----------|
| `/termos` | Termos de Uso (página React com markdown renderizado) |
| `/privacidade` | Política de Privacidade (página React com markdown renderizado) |

Ambas acessíveis sem login.

### Footer do portal

Link "Termos de Uso" e "Política de Privacidade" em todas as páginas.

---

## Checklist LGPD — MVP

| Item | Status |
|------|--------|
| Política de Privacidade publicada | Pendente |
| Termos de Uso publicados | Pendente |
| Checkbox de consentimento no signup | Pendente |
| Aviso ao vendedor no Telegram | Pendente |
| Deleção automática de áudio (24h) | Spec 03 |
| Deleção de dados de trial expirado (7d) | Spec 02/05 |
| RLS por org_id | Spec 02 |
| HTTPS em tudo | Spec 07 |
| Email de contato para privacidade | Pendente |
| Processo de exclusão de dados sob demanda | Pendente |
