# Verificação das correções — 05/11/2026

Projeto: `C:\Users\gabriel\Desktop\Antigravity PJ`.
Estado inicial: branch `main`, commit `df6ca3b`, somente `audit_tests/` não versionado.
Nenhuma instrução AGENTS.md encontrada no projeto. Arquivos da auditoria preservados.
`requirements.txt` inspecionado e mantido; não foi necessário adicionar dependências.
`history.json` não foi alterado nesta implementação (10 IDs legados).

## Execução reproduzível

```text
python -m unittest discover -s tests -v
python tools/run_regressions.py
```

O segundo comando executa a mesma suíte com HTTP externo bloqueado, `.env` desativado
e credenciais fictícias, e grava [resultado estruturado](regression-results.json).
Primeira etapa: **58/58 testes**, em Python 3.15.2 / Windows.
Continuação da revisão: **73/73 testes em Python 3.11.18**, sem falhas, erros ou skips.
O Python 3.11 foi instalado em ambiente isolado `.venv/review311`, com as dependências
existentes, sem mudar `requirements.txt`. Houve execução real nessa versão; o workflow
remoto do Actions não foi acionado.
`git diff --check` sem erros; `git diff --exit-code -- history.json` sem alterações.

Os testes usam respostas Gemini e Telegram simuladas. Eles comprovam os controles
e a recuperação; não medem a capacidade factual de um modelo real nem comprovam
publicação em Telegram. Nos testes offline não houve chamada Gemini real. A prévia
real separada está descrita ao final. Não houve envio real ao Telegram nem push do
repositório do usuário. Os testes de persistência criam remotes bare locais temporários.

## Evidências por requisito

| Área | Resultado demonstrado |
| --- | --- |
| Defeitos anteriores | Novos testes inicialmente falharam por item sem parecer mantido, aprovação por título, status inválido, corte internacional na prévia, histórico corrompido silencioso e retenção arbitrária. |
| Seleção | Catálogo determinístico com reserva 4:3, categoria por assunto, ambíguos explícitos, diversidade por veículo, vagas redistribuídas e teto global. Inverter feeds/candidatos preserva resultado; a deduplicação escolhe a representação mais completa deterministicamente. |
| Referências | URL inventada, outro artigo do mesmo domínio e ID desconhecido são rejeitados. Geração e revisão recebem snapshots idênticos do catálogo. URLs/nomes finais vêm do catálogo. |
| Revisão | Parecer ausente, duplicado, de outro ID/hash, sem status ou com status desconhecido bloqueia. Mudança posterior de contexto ou evidência invalida aprovação. |
| Correções | Todos os campos são exigidos; objeto corrigido é reavaliado. Timeout ou limite esgotado bloqueia. String de resumo ou correção vazia não aprova o original. |
| Panorama | Versão vinculada à seleção exata. Parecer negativo/observação impede publicação. Panorama intermediário vazio permite regeneração, mas não publicação. Após corte/reposição, outra geração e revisão são obrigatórias. |
| Cotas | Testes obtêm 4 BR + 3 MUNDO após reposição, inclusive rejeição no parecer final. Limites são aplicados em Python. Evento duplicado não completa cota. IDs tentados são excluídos explicitamente. Insuficiência informa faltas; não amplia janela. |
| Conteúdo | Título isolado não sustenta notícia. Lead curto tem teto proporcional e limitação; corpo público limitado pode enriquecer candidatos. Metadado de restrição impede uso de corpo embutido; navegação/publicidade não entra no texto. |
| Erro na fonte | Busca outra fonte autorizada no catálogo, exige trechos literalmente presentes e nova revisão. Aliases da Folha, Valor e Lupa consolidam o veículo; domínios distintos do mesmo veículo não contam como confirmação independente. Divergência é atribuída, sem solução inventada. |
| Entrega parcial | Primeiro recibo preservado; reinício envia só a segunda parte pendente da edição congelada. Uma notícia dividida só entra no histórico quando todas as suas partes são confirmadas. |
| Confirmação incerta | ReadTimeout, erro de conexão e recibo inválido não provocam retry cego. ConnectTimeout anterior à conexão fica pendente. Crash após intenção durável vira incerto e bloqueia envio automático. |
| Persistência entre runners | Clone A confirma parte 1 e falha na parte 2; clone B recupera do remoto e envia apenas parte 2. SHA remoto é conferido. Atualização concorrente rejeita checkpoint antes do POST. |
| Recuperação | Falha de checkpoint antes de POST impede envio; falha depois de POST deixa `sending` no último estado durável. Reconciliação manual do último recibo conclui e persiste a edição, liberando a seguinte. |
| Histórico | Migração legada preserva IDs, retenção por datas com desempate determinístico. Corrupção bloqueia também retomadas. Falha de replace atômico preserva arquivo anterior. |
| Prévia | Arquivos de produção comparados byte a byte antes/depois; nenhum POST, outbox, lock ou push. Fallback inclui internacionais após os primeiros 25 artigos. |
| Formatação | HTML/entidades balanceados, preservação de conteúdo longo, todas as partes dentro do teto conservador de 4.000 unidades UTF-16, mapa de IDs por parte. Rodapé usa 16:47 da revisão no teste, não 17h presumidas. |
| Agendamento | Cron existente `0 20 * * 1-5` preservado. Grupo de concorrência sem cancelar execução ativa, checkout atualizado e checkpoints `always()` após falhas. |

## Endereços consultados ao vivo

Consultas read-only em 05/11/2026 aproximadamente 20:36 BRT. Detalhes, datas das
entradas, links de amostra e resultados dos artigos em [feed-checks.json](feed-checks.json).

| Endereço | Observação e decisão |
| --- | --- |
| `https://www.nexojornal.com.br/rss.xml` | 200, 20 entradas, 8 datadas nas últimas 24h; ativado. Artigo de amostra: 200, extrator não identificou corpo; usar trecho se suficiente. |
| `https://www.nexojornal.com.br/feed/` | 404 nesse endereço; não ativado. |
| `https://feeds.a.dj.com/rss/RSSWorldNews.xml` | 200, 20 entradas; mais recente 27/01/2025, nenhuma nas últimas 24h; mantido desativado. Artigo de amostra: 401. |
| `https://feeds.content.dowjones.io/public/rss/RSSWorldNews` | 200, 74 entradas, 16 datadas nas últimas 24h; ativado. Transporte Dow Jones separado de artigos `wsj.com`. Amostra de artigo: 401, corpo não utilizado. |
| `https://www.ft.com/rss/home/international` | 200, 12 entradas atuais; alternativa validada, sem duplicar o feed world na configuração. Artigo de amostra: 403. |
| `https://www.ft.com/rss/world` | Redirecionou para `/world?format=rss`, 200, 25 entradas atuais; ativado. Artigo de amostra: 403, corpo não utilizado. |

Não foi inferida a causa de 401/403/404, nem indisponibilidade de um veículo inteiro.
Feeds disponíveis não comprovam acesso integral. As consultas iniciais no sandbox
retornaram ConnectionError; foram repetidas com rede autorizada para obter HTTP real.

## Auditoria anterior preservada

Os resultados abaixo pertencem à etapa anterior. Nesta continuação, `audit_tests/`
foi preservado e comparado por hash, sem adaptar seus testes nem repeti-los.

Antes das mudanças: 17 testes, todos passaram, incluindo testes que reproduzem os
defeitos em vez de exigir sua rejeição. Depois: 17 executados, 8 passaram e 9 ficaram
incompatíveis (5 falhas de asserção, 4 erros). Não foram alterados para aparentar sucesso.

Incompatibilidades:

- `test_domain_validation_matrix`: esperava autorizar domínio de transporte como editorial.
- `test_a1_all_approved`, `test_a2_item_rejected_is_excluded`, `test_a4_all_rejected`:
  usam pareceres somente por título, sem IDs/hashes exigidos.
- `test_a3_correction_applied`: exige publicar correção de resumo sem nova revisão.
- `test_f1_reviewer_timeout_blocks_bulletin`, `test_f3_rejection_of_single_item`,
  `test_m4_same_edition_run_twice_deduplication`: injetam rascunhos antigos sem IDs e
  aprovações; os testes novos exercitam esses caminhos com o contrato atual.
- `test_f4_correction_without_text_flaw`: acessa notícias mesmo quando a revisão inválida
  agora bloqueia o boletim.

`test_hallucinated_link_replacement_behavior` passa na auditoria antiga porque replica
o algoritmo defeituoso dentro do próprio teste; não chama a implementação corrigida.
`test_m5_partial_delivery_failure_recovery` não chega ao envio parcial (coleta vazia)
e espera reenvio integral futuro. Esses dois não servem como regressão dos requisitos;
as suítes `tests/test_editorial.py` e `tests/test_delivery.py` testam os caminhos reais.

## Revisão independente

Cinco achados importantes foram reproduzidos e corrigidos com regressões RED→GREEN:
rejeição final sem reposição; repetição de IDs rejeitados; seleção por ordem de feeds;
aliases do mesmo veículo usados como segunda fonte; edição reconciliada mantida parcial.
Nenhum achado foi adiado. Decisões operacionais e limites estão no README; não foi
feito deploy, commit ou push do projeto. Permissões reais do token GitHub, branch
protegida e recibos reais do Telegram dependem da execução de produção.

## Continuação: cinco pendências da revisão

Escopo limitado aos cinco defeitos relatados; sem nova arquitetura, troca de modelo,
alteração de histórico de produção ou mudança de agendamento.

Regressões em `tests/test_review_followup.py`: execução inicial de 15 casos apresentou
10 falhas que reproduziram os defeitos e 5 controles já corretos. Após as alterações,
os 15 casos passaram em Python 3.11.18. A suíte completa foi então executada **uma vez**:
73 casos passaram em 19,367 segundos, com HTTP bloqueado, Gemini/Telegram simulados
e Git em remotes bare locais. Comandos utilizados:

```powershell
# RED: antes das correções, no interpretador disponível
python -m unittest tests.test_review_followup -v
# GREEN: ambiente 3.11 isolado
.\.venv\review311\Scripts\python.exe -m unittest tests.test_review_followup -v
# Suíte completa: uma execução após as correções
.\.venv\review311\Scripts\python.exe tools/run_regressions.py
```

| Defeito | Correção | Regressões e resultado |
| --- | --- | --- |
| Corpo de matéria relacionada escolhido por tamanho | O extrator recebe a URL solicitada. Seleciona por URL, canonical da mesma origem, mainEntityOfPage ou @id; normaliza hostname/porta padrão, fragmento e rastreamento sem apagar query semântica. Corpos conflitantes, sem identidade ou de outra matéria são descartados. O enriquecimento e a ferramenta de inspeção passam a identidade. | `BodyIdentityTests`: principal versus relacionada mais longa, conflitos de identidade, entidade não correspondente e identificadores relativos/com fragmento; passaram. |
| Edição atual ignorada após recuperação de antiga | `_run` continua após confirmar uma edição de data anterior. Recarrega o histórico antes da coleta de hoje, removendo os itens recém-entregues. Mantém retorno imediato para edição atual e bloqueio em entrega parcial/incerta. | `FollowupMainTests`: confirmou ontem e coletou hoje sem repetir o artigo; pendente/incerta bloqueou coleta; retomada de hoje não duplicou edição. Todos passaram. |
| Script paywall.js bloqueava conteúdo livre | Removida a busca indiscriminada de palavras no HTML. Acesso é avaliado na entidade correspondente e em sinais de restrição no artigo visível. Restrição de uma relacionada não bloqueia a principal pública; restrição da principal bloqueia corpo embutido e fallback DOM. | `test_free_article_with_paywall_script_is_still_public`, `test_related_restricted_entity_does_not_block_public_primary`, `test_primary_restriction_blocks_its_body_and_dom_fallback`: passaram. |
| Título sem espaços de 4.100 caracteres derrubava formatação | `bind_item` rejeita título acima de 240 caracteres, campos acima do teto e tokens/links que não cabem com escape e margem de markup. O item inválido não chega à revisão/publicação; a reposição segue geração e revisão por versão. Não há truncamento factual. | `test_4100_character_unbroken_title_is_rejected_before_review_or_format` e `test_invalid_long_field_is_replaced_and_substitute_is_reviewed`: passaram; conferem substituta aprovada e tamanho final com cabeçalho/rodapé. A regressão anterior de conteúdo longo legítimo também passou na suíte completa. |
| Recibo de @canal interpretado como incerto | Suporte a @username mantido. Recibo é conferido pelo username e ID numérico; outbox guarda ambos, mantendo o destino @canal congelado. Recibo incompatível continua incerto. | Três testes de recibos em `FieldAndReceiptTests`: sucesso correspondente, username incompatível e retomada de checkpoint com destino preservado; passaram. |

Identidade e acesso seguem os campos documentados por
[Schema.org: mainEntityOfPage](https://schema.org/mainEntityOfPage) e
[isAccessibleForFree](https://schema.org/isAccessibleForFree). O recibo usa os campos
da [Chat do Telegram](https://core.telegram.org/bots/api#chat).

## Prévia REAL: tentativa encerrada por HTTP 500 do Gemini

Execução em **05/11/2026, 21:18:53–21:19:39 BRT**, Python 3.11.18, com RSS e chave
Gemini existentes, mantendo `gemini-3.1-flash-lite`. Uma única execução de
`main(preview=True)`, sob limite de oito chamadas e interrupção na primeira falha
técnica do serviço. Usou **duas chamadas reais**, abaixo do limite; a segunda retornou
`InternalServerError`, **HTTP 500**, mensagem `500 Internal error encountered.`
A tentativa foi encerrada com **código de saída 4**, sem troca de modelo ou nova tentativa.
Isso demonstra falha dessa requisição; não prova indisponibilidade permanente do modelo,
problema de chave, cota ou ausência de material elegível.

Coleta real: **221 matérias únicas**, **219 fora do histórico**, **35 candidatas**.
As classificações preliminares do catálogo foram **18 BR, 13 MUNDO e 4 MISTO**;
não são contagens de um boletim aprovado. Não houve seleção final liberada:
**0 itens de prévia aprovada BR / 0 MUNDO**, nenhum panorama final e nenhuma parte
formatada. Portanto não existe prévia completa para exibir nesta tentativa, nem é
possível atribuir a falta de sete notícias à insuficiência de fontes.

Fontes das 35 candidatas: G1 (4), Poder360 (4), BBC News Brasil (4), Folha (3),
NYT (3), Nexo (3), DW (3), FT (3), WSJ (3), Agência Lupa (3) e The Economist (2).
**4 candidatas tinham corpo identificado e 31 permaneciam com trecho RSS.**
Entre as 14 leituras adicionais: 4 corpos públicos extraídos, 4 HTTP 403, 1 HTTP 401,
2 restrições declaradas na matéria correta, 2 corpos não identificados/ambíguos e
1 entidade não correspondente. As outras 21 não tiveram corpo solicitado dentro
dos limites existentes. Endereços e resultados individuais constam no JSON abaixo;
essas observações não diagnosticam o veículo inteiro nem a causa dos códigos HTTP.

- [Resultado completo da prévia real](real-preview-results.json): URLs, fontes,
  níveis de evidência, limitações, erro do serviço, contagens e código de saída.
- [Log completo da execução real](real-preview-followup-output.txt).
- [Resultado da suíte offline em Python 3.11](regression-results.json).

Envio ao Telegram e checkpoint Git estavam explicitamente bloqueados no verificador.
Hashes de `history.json` iguais antes/depois; `delivery_state.json` continuou ausente.
As 11 entradas do [baseline de preservação](review-baseline-hashes.json), incluindo
workflow e arquivos de auditoria, permaneceram idênticas. `git diff --check` passou.
O HEAD local permanece `df6ca3b`; esta etapa não criou commit, push ou deploy. As
mudanças anteriores e as cinco correções permanecem locais. O remoto não foi alterado
por esta etapa; não foi feita consulta de sincronização com ele.

## Finalização em 06/11/2026

### Diagnóstico da cota BR

A prévia anterior tinha 18 candidatos BR, 13 MUNDO e 4 MISTO. Seu registro
preservou seis chamadas: redação, revisão, duas reposições, panorama e revisão
final. As reposições não chegaram a produzir novos itens válidos dentro das cotas
para revisão. Não há propostas brutas nem pareceres por ID guardados naquela
execução: quantos BR foram propostos, rejeitados ou corrigidos é **indeterminável**.
O resultado 1 BR/3 MUNDO não comprova falta de fontes. Não atribuímos ao modelo
rejeições editoriais que não foram registradas.

Defeitos locais reproduzidos: rascunhos inválidos eram descartados silenciosamente,
seus IDs podiam voltar nas reposições, e o modelo não recebia o teto exato de
palavras exigido pelo validador para evidência curta (mínimo 60, máximo 180,
ou 1,7 vezes as palavras disponíveis). A meta genérica de 100–160 podia ultrapassar
esse teto. O prompt agora explicita vagas por país e limites por evidência; IDs
inválidos são registrados e excluídos. Pareceres registram ID, versão e motivo.
Uma substituta aprovada da mesma categoria resolve a falha anterior; falha de
contrato não resolvida com cota incompleta bloqueia como técnica, não como falta
de material. Nenhum teto, fonte autorizada ou critério de aprovação foi relaxado.
Esses defeitos explicam um mecanismo possível da falha antiga, cuja frequência
exata não pode ser reconstruída sem as respostas que não foram retidas.

### Verificação final

Regressões RED→GREEN em `tests/test_pipeline.py`: orçamento explícito, retenção
de IDs inválidos e bloqueio de falha técnica mesmo com catálogo esgotado.
Testes afetados passaram. A primeira suíte foi interrompida pelo reinício da sessão;
revelou um teste com data fixa antiga e saída Windows sem UTF-8. O teste de retomada
agora cria edição da data corrente; os comandos usam `PYTHONUTF8=1`.
Após corrigir a distinção técnica/editorial final, **76/76** passaram em Python
**3.11.18**, 18,764 s, sem HTTP externo; resultado em `regression-results.json`.
A repetição da suíte foi motivada por falhas e mudança de código; não houve nova
prévia real. `git diff --check` e compilação da ferramenta de prévia passaram.

### Única prévia real desta sessão

Em 06/11/2026, 18:55:55–18:56:26 Brasília: 309 artigos, 35 candidatos
(18 BR, 13 MUNDO, 4 MISTO), **4 BR e 3 MUNDO aprovados**, código **0**, 30,390 s.
Quatro chamadas ao `gemini-3.1-flash-lite`: geração 6,969 s, revisão 4,234 s,
panorama 1,469 s, revisão final 4,078 s. Limite de oito chamadas, sem fallback,
sem erro HTTP, parsing ou validação. Nenhuma reposição necessária. Quatro BR
propostos, quatro aprovados em ambas as revisões; zero rejeitados/corrigidos ou
ignorados na geração. Um MISTO foi classificado BR e outro MUNDO pela redação,
confirmados pela revisão. Os demais candidatos não foram propostos nesta edição.

Telegram, subprocessos Git, checkpoints e gravações de histórico/outbox foram
bloqueados no verificador; hashes de produção permaneceram iguais. A prévia leu
o histórico local intacto. Após ela, os sete IDs aprovados foram comparados ao
histórico remoto `8082a588715301e80cdd2ea65f49809642fb96a9`: interseção vazia.
Não houve envio ao Telegram. O HTML completo foi recuperado literalmente do stdout
pois o fluxo de prévia imprime diretamente, em vez de chamar o remetente; a
ferramenta agora também captura esse caminho. Sem repetição de chamadas reais.

- [Boletim completo em HTML](final-preview.html)
- [Etapas, propostas, pareceres, hashes e resultado](final-preview-results.json)
- Ferramenta reproduzível: `tools/final_preview.py` (não executar novamente nesta sessão).

### Publicação e operação

Remoto confirmado: `bolachamolhada1-maker/boletim-noticias`, padrão `main`.
O remoto avançou apenas `history.json`; a integração deve preservar essa versão,
sem sobrescrevê-la pelo arquivo local anterior. Workflow remoto ativo, Python 3.11,
cron `0 20 * * 1-5`, janela 24h/72h na segunda. Nomes dos três secrets existentes
conferidos: `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, sem valores.
Dependências continuam em `requirements.txt`. Nenhuma execução manual disparada.
O pacote Gemini instalado emite aviso de depreciação; a migração de SDK permanece
fora deste escopo. Revisão semântica depende do modelo e não é certificação factual.
Próxima ocorrência do cron após esta sessão: **09/11/2026 às 17h America/Sao_Paulo**
(20h UTC), sujeita a atraso do agendador. A execução de hoje já terminou antes da
publicação, com sucesso reportado pelo Actions; isso não comprova recibo Telegram.

Auditoria preexistente preservada sem editar: whitespace legado em audit_tests/
permanece; diff-check passou com essa excecao de espacos finais. Nenhuma credencial
do .env foi encontrada nos arquivos selecionados, conferidos antes do commit.
