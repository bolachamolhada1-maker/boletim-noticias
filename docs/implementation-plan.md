# Correções do boletim — plano de implementação

Pedido: corrigir o projeto existente, manter Python/Gemini/Telegram/GitHub Actions,
4 notícias BR e 3 MUNDO quando comprováveis, janela de 24h (72h na segunda),
cron de dias úteis às 17h BRT. A implementação segue diretamente o escopo autorizado.

## Diagnóstico inicial

- `news_bot.py`: cortes independentes por posição; classificação pelo feed;
  URL inventada substituída por outra matéria; revisão permissiva por título;
  correções e panorama sem aprovação da versão final; histórico salvo só ao fim.
- Workflow real: `.github/workflows/news_bot.yml`; cron correto; sem serialização;
  persistência não executada após falha; push apenas depois de toda a entrega.
- `audit_tests/` já existia e está não versionado. Preservar integralmente.
  Alguns testes caracterizam ou exigem os defeitos anteriores.
- Sem AGENTS.md dentro do projeto. `history.json` existente contém 10 IDs.

## Arquitetura

Manter os pontos de entrada do bot, separando estado de entrega em módulo pequeno.
Catálogo compartilhado e imutável por execução: IDs estáveis, evidência com nível,
classificação por assunto (ambiguidades explícitas), seleção determinística e diversa.
Referências vêm do catálogo. Pareceres usam ID e hash de todos os campos publicados
e das evidências. Só aprovação explícita libera; correções voltam à revisão.
Após rejeições/reposições, revisar novamente conjunto e panorama apoiado nele.

Congelar partes antes do envio; checkpoints atômicos e, no Actions, commits/push
síncronos antes e depois de cada requisição. Estado `sending` durável evita reenvio
automático quando confirmação se perde. Não prometer entrega exatamente uma vez.

## Tarefas e verificação

- [x] Escrever e executar regressões RED para revisão permissiva, corte internacional,
  associação incorreta e corrupção de histórico.
- [x] Corrigir catálogo, seleção, coleta limitada e revisão estrita; validar regressões.
- [x] Adicionar regressões de envio parcial, timeout incerto, reinício e erro de push;
  implementar estado persistente compatível e workflow serializado.
- [x] Corrigir limites de HTML/partes, rodapé com hora real e prévia sem efeitos.
- [x] Verificar endereços de Nexo/WSJ/FT sem inferir indisponibilidade do veículo;
  documentar resultados e manter desativado o que não foi validado.
- [x] Executar suíte nova completa e auditoria anterior; documentar divergências,
  evidências e limitações. Não enviar mensagens nem consumir Gemini real nos testes.

## Foco da revisão final

Esquemas ausentes/duplicados/trocados; hash de versão obsoleto; panorama após corte;
reinício entre envio e confirmação; push rejeitado; HTML grande com entidades;
classificação em feeds mistos; fontes de transporte versus editoriais; prévia.
