# 📰 Boletim Automático de Notícias

Automação jornalística completa que coleta, filtra, redige, audita editorialmente e entrega um boletim diário de notícias no Telegram com custo **R$ 0,00/mês**. 
Utiliza **Google Gemini** como IA editorial em duas etapas e **GitHub Actions** para agendamento autônomo na nuvem (executa diariamente às 17h de Brasília, mesmo com o computador desligado).

---

## 🚀 Como Funciona o Fluxo

1. **Coleta Confiável & Fontes Autorizadas:** Monitora feeds RSS exclusivamente de veículos autorizados (Folha de S.Paulo, G1, Poder360, Agência Lupa, BBC News Brasil, Deutsche Welle, The New York Times, The Economist, BBC News) com validação de domínios na raiz, cabeçalhos adequados, timeout e proteção contra SSRF.
2. **Filtragem & Deduplicação:** Remove notícias já enviadas (histórico de envios reais) e filtra estritamente por **Política, Economia, Segurança Pública e Tecnologia**, excluindo fofocas, esportes e entretenimento.
3. **Etapa 1 — Redação Aprofundada com IA:** O **Google Gemini** analisa o material-fonte encapsulado em tags `<artigo>` e redige até 7 notícias (4 do Brasil + 3 Internacionais de acontecimentos distintos), com ~100 a 160 palavras por matéria, contendo:
   - Título informativo e sóbrio.
   - Resumo desenvolvido (o que aconteceu, quem, quando e onde, com números e dados).
   - Contexto amplo e histórico necessário.
   - Consequências confirmadas e próximos passos.
   - Repercussão quando houver.
   - Nome do veículo autorizado e link direto da matéria original.
4. **Etapa 2 — Auditoria Editorial Automática Obrigatória:** Chamada separada e independente ao Gemini que atua como checador de fatos. Verifica se cada alegação tem suporte direto nos textos coletados, se as 3 internacionais cobrem fatos distintos e se datas/cifras conferem. Rejeita itens sem evidência factual antes do despacho.
5. **Formatação & Divisão Inteligente (HTML):** Formatação em HTML nativo com escape de caracteres (`html.escape`). Divide a entrega em partes numeradas sem truncar ou reduzir as matérias a manchetes.
6. **Entrega no Telegram:** Disparo via API com fallback para texto puro caso ocorra qualquer erro de entidade.
7. **Histórico Inteligente:** Salva no `history.json` apenas as notícias efetivamente entregues.

---

## 🔒 Arquitetura de Segurança Implementada

- **Fontes Exclusivamente Autorizadas:** Validação estrita de domínio na coleta e na auditoria final contra a lista restrita de veículos autorizados.
- **Auditoria Editorial Obrigatória:** Etapa independente que impede o envio de notícias com alucinações ou sem respaldo factual nas fontes.
- **Proteção contra Vazamento de Chaves:** Nenhum token ou chave de API no código-fonte. Localmente no `.env` (ignorado pelo `.gitignore`); no GitHub, ficam salvos nos **Repository Secrets**.
- **Defesa contra Prompt Injection:** Feeds externos tratados como dados brutos dentro de tags XML com `response_mime_type="application/json"`.
- **Prevenção de SSRF e DNS Rebinding:** Inspeciona URLs de feeds e redirecionamentos resolvendo IPs para bloquear redes internas e privadas.
- **Resiliência Multi-Modelo:** Fallback sequencial automático entre múltiplos modelos (`gemini-3.1-flash-lite` → `gemini-3.5-flash-lite` → `gemini-3.8-flash`).

---

## 🕒 Horários e Frequência

- **Segunda a Sexta-feira às 17h (Horário de Brasília / UTC-3):** Acionado via cron `0 20 * * 1-5` no GitHub Actions.
- **Terça a Sexta-feira:** Cobertura das últimas 24 horas.
- **Segunda-feira:** Edição especial com janela estendida de 72 horas (cobre o fim de semana completo + segunda-feira).

---

## 🛠️ Comandos Úteis

### Execução Local
```bash
# Instalar dependências
pip install -r requirements.txt

# Gerar prévia no terminal (não envia ao Telegram)
python news_bot.py --preview

# Executar e enviar para o Telegram
python news_bot.py

# Descobrir o Chat ID do seu Telegram
python get_chat_id.py
```

### Disparo Manual na Nuvem
1. Acesse o repositório no GitHub.
2. Vá na aba **Actions** → selecione **Boletim de Notícias** à esquerda.
3. Clique em **Run workflow**.
