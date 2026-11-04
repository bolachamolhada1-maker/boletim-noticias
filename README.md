# 📰 Boletim Automático de Notícias

Automação que coleta, resume e envia um boletim diário de notícias pelo Telegram, usando Google Gemini como IA e GitHub Actions para agendamento gratuito na nuvem.

## O que faz

- Coleta notícias de **política, economia, segurança e tecnologia** do Brasil e do mundo
- Seleciona as 6 mais relevantes do dia (4 do Brasil + 2 do mundo)
- Gera um **panorama executivo** + **resumo detalhado** de cada notícia com repercussão
- Envia automaticamente para o seu Telegram **de segunda a sexta às 18h (Brasília)**
- Na segunda-feira, inclui o resumo do fim de semana
- **Custo: R$ 0,00/mês**

---

## ⚙️ Configuração inicial (faça uma vez)

### 1. Instale as dependências (para rodar localmente)

```bash
pip install -r requirements.txt
```

### 2. Configure o arquivo `.env`

Copie o exemplo abaixo e preencha com suas chaves:

```
GEMINI_API_KEY=sua_chave_aqui
TELEGRAM_BOT_TOKEN=seu_token_aqui
TELEGRAM_CHAT_ID=seu_chat_id_aqui
```

### 3. Obtenha seu Chat ID do Telegram

1. Abra o Telegram e busque por **@jornaltom_bot**
2. Clique em **Iniciar** ou envie qualquer mensagem
3. Execute:

```bash
python get_chat_id.py
```

4. Copie o número exibido e cole no `.env` em `TELEGRAM_CHAT_ID=`

### 4. Configure os segredos no GitHub

No seu repositório GitHub:
- Vá em **Settings → Secrets and variables → Actions → New repository secret**
- Adicione os 3 segredos abaixo (use exatamente esses nomes):

| Nome do Segredo | Valor |
|---|---|
| `GEMINI_API_KEY` | Sua chave do Google AI Studio |
| `TELEGRAM_BOT_TOKEN` | Token do bot (começa com números) |
| `TELEGRAM_CHAT_ID` | O número obtido no passo 3 |

---

## 🚀 Como usar

### Testar localmente (prévia sem enviar)

```bash
python news_bot.py --preview
```

### Executar e enviar de verdade

```bash
python news_bot.py
```

### Disparar manualmente pelo GitHub

1. Vá em **Actions → Boletim de Notícias → Run workflow**
2. Escolha se quer gerar prévia ou enviar de verdade

---

## 🛠️ Manutenção

### Alterar fontes RSS

Edite o arquivo `config.py` → lista `RSS_FEEDS`.

### Alterar quantidade de notícias

Edite `config.py` → `MAX_NEWS_TOTAL`, `MAX_NEWS_BRAZIL`, `MAX_NEWS_WORLD`.

### Alterar horário de envio

Edite `.github/workflows/news_bot.yml` → campo `cron`.  
Lembre-se: o GitHub usa UTC. Brasília = UTC-3.  
Exemplo: 18h BRT = 21h UTC = `0 21 * * 1-5`

### Pausar temporariamente

No GitHub: **Actions → Boletim de Notícias → ⋯ → Disable workflow**

### Reativar

No GitHub: **Actions → Boletim de Notícias → Enable workflow**

### Consultar erros

No GitHub: **Actions** → clique na execução com ✗ → veja os logs de cada etapa.

### Resetar o histórico (reenviar notícias antigas)

Delete ou esvazie o arquivo `history.json` no repositório.

---

## 📋 Arquitetura

```
news_bot.py       → Script principal (coleta, filtra, resume, envia)
config.py         → Fontes RSS, temas, limites e configurações
get_chat_id.py    → Utilitário de configuração do Telegram
history.json      → Histórico de notícias já enviadas (gerado automaticamente)
.env              → Credenciais locais (nunca vai para o GitHub)
.github/
  workflows/
    news_bot.yml  → Agendamento automático no GitHub Actions
```

## ⚠️ Limitações conhecidas

- O GitHub Actions pode atrasar o disparo do cron em até 15-30 minutos em horários de pico
- O plano gratuito do GitHub desativa workflows em repositórios sem commits por 60 dias — faça ao menos um commit pequeno por mês se necessário
- A API gratuita do Gemini tem limite de requisições por minuto — para uso pessoal com 1 execução/dia, não é um problema
- Notícias por trás de paywall aparecem apenas com o trecho disponível no RSS
