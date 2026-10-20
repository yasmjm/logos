# ADR 0001: Rate limit em memória

- **Status:** aceito
- **Data:** 2026-10-20

## Contexto

Duas rotas precisam de limite de requisições:

- `POST /auth/login`: 5 tentativas por minuto por IP, contra força bruta de senha.
- `POST /incidents` (ingestão): 120 requisições por minuto por chave de API, contra integrações com defeito ou abuso da chave.

Ao exceder o limite, a API responde `429` em `application/problem+json`, com o header `Retry-After`.

O MVP roda numa única instância e não tem Redis nem outro armazenamento compartilhado.

## Decisão

Usar uma janela deslizante em memória (`app/core/rate_limit.py`), aplicada como dependência nas duas rotas, sem dependência externa.

- **Por que não o `slowapi`:** exige decorators e um parâmetro `request` em cada rota, e traria uma dependência para cerca de 40 linhas de código.
- **Quando contar:** no login, contam todas as tentativas (certas e erradas). Na ingestão, a contagem acontece só depois de validar a chave, então chaves inválidas recebem `401` e não consomem a cota da chave válida. A chave nunca é guardada em texto: a contagem usa o SHA-256 dela.

## Limitações

1. **Não funciona com várias instâncias.** Cada processo tem os próprios contadores. Com N instâncias ou N workers do uvicorn, o limite efetivo vira N × o configurado.
2. **Contadores zeram a cada restart e a cada deploy.**
3. **IP atrás de proxy.** Na plataforma de deploy, a requisição chega pelo proxy ou load balancer. Sem configuração, `request.client.host` é o IP do proxy, e o limite do login passa a valer **para todos os usuários juntos**: cinco erros de qualquer pessoa bloqueiam o login de todo mundo por um minuto.

## Consequências e próximos passos

- **No deploy** (tarefa de deploy), o uvicorn deve rodar com `--proxy-headers` e `--forwarded-allow-ips` configurado com os IPs do proxy da plataforma. Sem isso, vale a limitação 3. Nunca confiar em `X-Forwarded-For` vindo de fora do proxy, porque o cliente pode forjá-lo.
- **Para escalar** além de uma instância, trocar o armazenamento por um compartilhado (por exemplo, Redis com contadores atômicos). A interface `RateLimiter.hit(key)` isola essa troca.
