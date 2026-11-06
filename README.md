# 📰 Boletim Automático de Notícias

Automação que coleta, filtra, redige, revisa e entrega notícias no Telegram.
Utiliza **Google Gemini** e **GitHub Actions**, agendado todos os dias às 17h de Brasília. A execução pode começar depois do horário agendado; o rodapé informa a hora real da revisão. Custos e cotas dependem dos planos dos serviços, da redação e das revisões necessárias; não há garantia de custo zero.

---

## 🚀 Como Funciona o Fluxo

1. **Coleta & Fontes Autorizadas:** Monitora os endereços em `config.py`, incluindo Nexo, WSJ e FT verificados. Separa domínio de transporte RSS de domínio editorial. Valida cada destino antes de redirecionar; limita bytes, tempo e tentativas. Registra título, trecho ou corpo acessível. Obtém corpo público apenas para candidatos selecionados, sem contornar restrições de acesso. Associa o corpo à identidade da matéria (URL/canonical/mainEntityOfPage/@id); entidades ambíguas ou de outra matéria são descartadas. Restrições são avaliadas na entidade correspondente; nomes de scripts como `paywall.js` não bloqueiam conteúdo público.
2. **Filtragem & Deduplicação:** Remove notícias já enviadas (histórico de envios reais) e filtra estritamente por **Política, Economia, Segurança Pública e Tecnologia**, excluindo fofocas, esportes e entretenimento.
3. **Redação com IA:** O **Google Gemini** recebe um catálogo compartilhado, com IDs estáveis. A seleção reserva vagas por assunto, prioriza relevância/atualidade e diversidade editorial e redistribui vagas de candidatos quando necessário. A classificação considera o assunto, inclusive em feeds mistos. O objetivo é 4 notícias BR e 3 MUNDO, com aproximadamente 100 a 160 palavras no conjunto de campos por matéria quando comprováveis. Com evidência curta, o texto é menor e identifica a limitação. Campos:
   - Título informativo e sóbrio.
   - Resumo desenvolvido (o que aconteceu, quem, quando e onde, com números e dados).
   - Contexto amplo e histórico necessário.
   - Consequências confirmadas e próximos passos.
   - Repercussão quando houver.
   - Nome do veículo autorizado e link direto da matéria original.
4. **Revisão obrigatória:** Outra chamada Gemini verifica fidelidade às evidências associadas, precisão, atribuição e acontecimentos distintos em todo o conjunto. Pareceres usam ID e hash de todos os campos publicados e das evidências. Ausência, duplicidade, status inválido ou versão divergente bloqueiam a publicação. Correções completas voltam à revisão. Há no máximo 3 tentativas por revisão e 2 rodadas de reposição. O panorama é gerado sobre a seleção final e revisado novamente com ela. Uma comparação com uma matéria não comprova independentemente a verdade dos fatos.
5. **Formatação & Divisão Inteligente (HTML):** Formatação em HTML nativo com escape de caracteres (`html.escape`). Divide a entrega em partes numeradas sem truncar ou reduzir as matérias a manchetes. Antes da revisão, rejeita título acima de 240 caracteres e tokens/campos incompatíveis com a formatação; reposições passam pela revisão normal. O teto final inclui cabeçalhos e rodapé.
6. **Entrega no Telegram:** Congela o conteúdo e o destinatário em `delivery_state.json` antes do envio. Cada parte tem ID e estado próprios. Preserva o recibo Telegram disponível e retoma apenas partes comprovadamente pendentes da mesma edição. Aceita ID ou `@canal`; nesse último caso, confere o username do recibo e persiste o ID numérico real sem substituir o destino congelado.
7. **Histórico:** Migra o formato anterior de `history.json` sem apagar IDs. Registra uma notícia quando todas as partes que a contêm têm confirmação. Usa gravação atômica e retenção determinística por data. Arquivo corrompido bloqueia a execução.

---

## 🔒 Arquitetura de Segurança Implementada

- **Fontes Exclusivamente Autorizadas:** Validação estrita de domínio na coleta e na auditoria final contra a lista restrita de veículos autorizados.
- **Revisão bloqueante:** Somente aprovação explícita da versão correspondente libera publicação. A qualidade semântica ainda depende do revisor Gemini; os testes automatizados validam os controles com respostas simuladas.
- **Proteção contra Vazamento de Chaves:** Nenhum token ou chave de API no código-fonte. Localmente no `.env` (ignorado pelo `.gitignore`); no GitHub, ficam salvos nos **Repository Secrets**.
- **Dados externos:** Catálogo e rascunhos são serializados como JSON e tratados como dados nas instruções do modelo. Isso reduz risco de injeção; não certifica imunidade do modelo.
- **Rede:** Bloqueia destinos privados e DNS não resolvido, valida redirecionamentos antes de acessá-los e limita processamento. A validação DNS não fixa o IP do socket; não é uma garantia absoluta contra DNS rebinding de um domínio autorizado comprometido.
- **Modelo:** Mantém `config.GEMINI_MODEL`. Fallbacks podem ser configurados explicitamente em `GEMINI_FALLBACK_MODELS`, com nomes disponíveis na conta. Nenhum modelo OpenAI é usado pelo bot.

---

## 🕒 Horários e Frequência

- **Todos os dias às 17h (Horário de Brasília / UTC-3):** Acionado via cron `0 20 * * *` no GitHub Actions, incluindo sábado e domingo.
- **Terça a Sexta-feira:** Cobertura das últimas 24 horas.
- **Segunda-feira:** Retrospectiva do fim de semana com atualizações da segunda, dentro das últimas 72 horas. Notícias já enviadas podem voltar à seleção por relevância e recebem identificação de recapitulação no texto submetido à revisão. Atualizações precisam de suporte nas evidências. Nos demais dias, inclusive sábado e domingo, a janela é de 24 horas e o histórico continua excluindo IDs já enviados. A mesma edição ou parte não é reenviada: a retomada usa o estado congelado existente.

---

## 🛠️ Comandos Úteis

### Execução Local
```bash
# Instalar dependências
pip install -r requirements.txt

# Gerar prévia no terminal (não envia ao Telegram)
python news_bot.py --preview

# Testes de regressão: sem Gemini/Telegram reais; Git usa remotes bare temporários
python -m unittest discover -s tests -v

# A mesma suíte com bloqueio adicional de HTTP e relatório em docs/regression-results.json
python tools/run_regressions.py

# Executar e enviar para o Telegram
python news_bot.py

# Descobrir o Chat ID do seu Telegram
python get_chat_id.py
```

### Disparo Manual na Nuvem
1. Acesse o repositório no GitHub.
2. Vá na aba **Actions** → selecione **Boletim de Notícias** à esquerda.
3. Clique em **Run workflow**.

## Estado, falhas e retomada

O workflow real é `.github/workflows/news_bot.yml`. Execuções de produção compartilham
uma fila (`cancel-in-progress: false`), usam a branch padrão e atualizam o checkout
após a espera. Cada transição de envio grava e confirma commit/push síncrono de
`history.json` e `delivery_state.json`. O passo final usa `always()` e preserva um
artefato de diagnóstico após falha. Um erro de push bloqueia o próximo envio;
conflitos não recebem force, merge ou rebase automático.

Estados de partes: `pending` (não enviada/rejeição confirmada), `sending` (intenção
durável antes da requisição), `sent` (recibo com message_id/chat_id) e `uncertain`
(a requisição pode ter chegado). Uma interrupção com `sending` é recuperada como
`uncertain`. ReadTimeout e erros de conexão sem comprovação não provocam reenvio
automático. ConnectTimeout anterior à conexão mantém `pending`. Não há promessa
de entrega exatamente uma vez: a API Telegram não oferece chave idempotente para
`sendMessage` ([documentação](https://core.telegram.org/bots/api#sendmessage)).

Para retomar partes pendentes, execute novamente: o bot lê a edição congelada antes
de coletar feeds ou chamar Gemini. Se concluir uma edição antiga, continua a edição
de hoje com o histórico atualizado; entrega anterior parcial/incerta bloqueia essa
continuação. Retomar a própria edição de hoje não cria outra edição. Uma parte incerta exige reconciliação humana no
Telegram. Confirme o recebimento e registre `status: sent`, `message_id`, `chat_id`
e `sent_at` no estado (também `chat_username` para destino `@canal`); só marque `pending` se a ausência tiver sido confirmada.
Faça isso com o workflow parado e preserve texto, IDs e manifesto. Persista o
estado corrigido na branch padrão antes de retomar. Sem comprovação, mantenha
`uncertain`. Branch protegida que rejeite checkpoints precisa permitir essa
gravação para a automação funcionar; o bot bloqueia o envio quando ela falha.

O arquivo de estado contém texto e referências publicados; nunca tokens. Não remova
edições incompletas. São retidas até 30 edições concluídas e 500 artigos no histórico.
Localmente a gravação é atômica em disco. No Actions, `BOT_PERSIST_GIT=1` habilita
a persistência entre runners. A prévia lê o histórico, pode consumir cota Gemini e
rede, mas não abre outbox, não envia, não grava arquivos de produção nem faz push.

Códigos de saída: `0` entrega completa com cotas; `2` ausência de candidatos;
`3` edição parcial/confirmacão incerta; `4` falha técnica/editorial/estado;
`5` material comprovável insuficiente (pode haver entrega de um boletim menor).
Saídas diferentes de zero ficam visíveis como falha no Actions, sem mensagem
enganosa de sucesso. O bot não amplia a janela temporal nem repete eventos para
completar as cotas.

## Resultados de verificação

Veja [relatório](docs/verification.md) e [consultas por endereço](docs/feed-checks.json).
Na continuação da revisão, **73/73 regressões offline passaram em Python 3.11.18**.
A tentativa separada de prévia real coletou RSS, mas terminou com código 4 após
HTTP 500 do Gemini na segunda chamada; não houve boletim final aprovado nem envio.
Fontes candidatas, limitações e erro estão em [real-preview-results.json](docs/real-preview-results.json).
`tools/check_feeds.py` repete a inspeção read-only de RSS e uma amostra de artigo,
sem Gemini/Telegram. Um 401, 403, 404 ou falha DNS vale para o endereço consultado
naquele momento; não diagnostica o veículo inteiro nem a causa do bloqueio.

A validação final e o diagnóstico da cota BR estão em [docs/verification.md](docs/verification.md).
O modelo recebe os tetos locais de palavras por evidência e as vagas BR/MUNDO.
Rascunhos inválidos têm seus IDs excluídos das reposições; falha de contrato não
resolvida bloqueia a publicação como técnica. Pareceres continuam obrigatórios
por ID e versão exata. A [prévia completa de 06/11/2026](docs/final-preview.html)
produziu 4 BR e 3 MUNDO; é apenas um artefato de validação, sem envio.
