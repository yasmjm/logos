# ADR 0002: Estratégia de resiliência

- **Status:** aceito
- **Data:** 2026-10-20

## Contexto

A central não pode ficar às cegas quando o banco oscila, seja por um restart, uma falha de rede ou lentidão. O sistema precisa:

- falhar rápido e de forma explícita;
- recuperar sozinho de falhas curtas;
- nunca duplicar o efeito de uma ação;
- permitir uma demonstração controlada desse comportamento.

## Decisão

1. **Timeouts e pool explícitos**, configuráveis por settings:
   - `connect_timeout` de 3 s e `statement_timeout` de 5 s no servidor;
   - `pool_size`, `max_overflow` e `pool_timeout` de 5 s;
   - `pool_pre_ping`, que descarta conexões mortas antes de entregá-las.
2. **Retry só onde é seguro**: na obtenção da conexão e nas leituras (listagem, detalhe, summary, autenticação e as leituras de diagnóstico depois de uma escrita que não afetou linhas).
   - Até 3 tentativas, com backoff exponencial e *full jitter* (espera sorteada entre 0 e 50 ms, depois entre 0 e 100 ms), para que clientes que falharam juntos não tentem de novo ao mesmo tempo.
   - Só falhas transitórias de conexão são repetidas: SQLSTATE classe `08`, `57P01` a `57P03` e conexão recusada ou perdida.
   - **Não são repetidos:** o *statement timeout*, porque repetir uma consulta lenta triplica a carga justamente quando o banco está sofrendo, e o pool esgotado, porque cada nova espera somaria mais 5 s.
   - Não usamos o `tenacity`: o helper tem cerca de 25 linhas e não justifica uma dependência.
3. **503, nunca 500**, para banco indisponível, pool esgotado ou timeout: `application/problem+json` com `Retry-After` e o `request_id` no corpo, para suporte.
4. **Health em duas rotas**: `/health` (liveness) não toca no banco, e `/ready` (readiness) faz `SELECT 1` com timeout de 1 s. Um banco fora tira a instância do balanceador sem que a plataforma a reinicie à toa.
5. **Observabilidade**: um `X-Request-ID` (recebido ou gerado) volta em toda resposta. Cada requisição gera uma linha de log JSON com `request_id`, método, rota (o template), status e duração.

## Por que não há retry de escrita no servidor

Depois de uma falha de conexão durante um `UPDATE` ou `COMMIT`, o servidor não sabe se a escrita foi aplicada: o commit pode ter acontecido e a resposta se perdido. Repetir às cegas poderia gravar duas vezes, por exemplo dois eventos `status_changed`.

Por isso o servidor responde 503, e quem repete é o cliente, sempre com a mesma `version`. O lock otimista torna essa repetição segura:

- **A primeira escrita não foi aplicada:** a `version` ainda confere, e a repetição faz o efeito uma única vez.
- **A primeira escrita foi aplicada:** a `version` já mudou, e a repetição recebe **409 com o `current`**, sem nenhum efeito novo. O cliente vê o estado real e decide.

O UPDATE filtra por `id` e `version` numa única instrução, então não há janela para duplicar o efeito.

## Por que o modo caos expira sozinho

O `/chaos` existe para demonstrar o comportamento acima: latência e 503 simulados, só em `/incidents`, nunca em `/health`, `/ready`, `/auth` ou `/chaos`.

- **Expira sozinho:** toda configuração vale por no máximo 3 minutos (`expires_at` na resposta) e se desliga sozinha. Um avaliador que esquecer o caos ligado não deixa o sistema quebrado para o próximo.
- **Desligado por padrão:** fica fora a menos que `CHAOS_ENABLED=true`. Desligado, nem a rota nem o middleware existem, e `/chaos` responde 404.

## Limitações

- O estado do caos fica em memória, assim como o do rate limit (ADR 0001): não é compartilhado entre instâncias e zera a cada restart.
- O retry cobre falhas curtas, de até algumas centenas de ms. Quedas longas dependem do `Retry-After` e da repetição pelo cliente.
