# 📰 Boletim Automático de Notícias

Automação jornalística completa que coleta, filtra, resume e entrega um boletim diário de notícias no Telegram com custo **R$ 0,00/mês**. 
Utiliza **Google Gemini** como IA editorial e **GitHub Actions** para agendamento autônomo na nuvem (roda mesmo com seu computador desligado).

---

## 🚀 Como Funciona o Fluxo

1. **Coleta Confiável (Anti-SSRF):** Monitora feeds RSS de veículos de referência (Agência Brasil, G1, Poder360, TecMundo e BBC News Brasil) com validação de cabeçalhos, timeout de 12s e proteção contra Server-Side Request Forgery.
2. **Filtragem & Deduplicação:** Remove notícias duplicadas e filtra estritamente por **Política, Economia, Segurança Pública e Tecnologia**, excluindo fofocas, esportes e entretenimento.
3. **Curadoria & Resumo com IA:** O **Google Gemini** analisa as notícias em lote isolado (delimitadas por XML para proteção contra prompt injection) e seleciona até 6 notícias (4 do Brasil + 2 do Mundo).
4. **Formato Editorial de Dois Níveis:**
   - ⚡ **Panorama do Dia:** Síntese executiva rápida no topo.
   - 📌 **Matérias Detalhadas:** Fatos estruturados com marcadores, contexto/desdobramentos práticos, visão leve a moderada de analistas/mercado e link direto para a matéria original.
5. **Entrega no Telegram:** Formatação em HTML nativo com escape estrito de caracteres (imune a falhas de markdown) e divisão inteligente de blocos caso a mensagem ultrapasse 4.000 caracteres.
6. **Histórico Inteligente:** Salva no `history.json` apenas as matérias efetivamente entregues, impedindo repetições sem descartar precocemente matérias não selecionadas.

---

## 🔒 Arquitetura de Segurança Implementada

- **Proteção contra Vazamento de Chaves:** Nenhum token ou chave de API fica registrado no código-fonte. No ambiente local, ficam no arquivo `.env` (ignorado pelo `.gitignore`); no GitHub, ficam salvos nos **Repository Secrets**.
- **Defesa contra Prompt Injection:** As notícias de feeds RSS externos são tratadas como dados brutos não confiáveis encapsulados em tags `<artigo>` e validadas com `response_mime_type="application/json"`.
- **Prevenção de SSRF e DNS Rebinding:** O script inspeciona a URL de cada feed e resolve o endereço de IP via socket para impedir requisições acidentais ou maliciosas a redes internas ou endereços locais (localhost, loopback, redes privadas RFC1918).
- **Imunidade a Erros de Parsing no Telegram:** Uso de HTML seguro com `html.escape()` em todos os campos dinâmicos, acompanhado de fallback automático para texto puro em caso de rejeição da API do Telegram.
- **Resiliência Multi-Modelo:** Fallback sequencial automático entre múltiplos modelos (`gemini-3.1-flash-lite` → `gemini-3.5-flash-lite` → `gemini-3.8-flash`) caso algum modelo atinja o limite temporário de requisições.

---

## ⚙️ Configuração dos Segredos no GitHub

No seu repositório no GitHub:
Acesse **Settings → Secrets and variables → Actions** e configure os 3 segredos:

| Segredo | Descrição |
|---|---|
| `GEMINI_API_KEY` | Chave gratuita de API gerada no Google AI Studio |
| `TELEGRAM_BOT_TOKEN` | Token do seu bot do Telegram (@jornaltom_bot) |
| `TELEGRAM_CHAT_ID` | Seu ID de usuário no Telegram |

---

## 🕒 Horários e Frequência

- **Terça a Sexta-feira às 18h (Horário de Brasília):** Cobre as notícias das últimas 24 horas.
- **Segunda-feira às 18h (Horário de Brasília):** Edição especial com cobertura estendida das últimas 72 horas (fim de semana completo + segunda-feira).

---

## 🛠️ Comandos Úteis

### Execução Local
```bash
# Instalar dependências
pip install -r requirements.txt

# Gerar prévia no terminal (não envia mensagem)
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
