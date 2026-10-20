# ADR 0001: Rate limit em memória

- **Status:** aceito
- **Data:** 2026-10-20 (atualizado no deploy, mesma data)

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

- **No deploy (Render):** o IP do cliente vem da entrada do `X-Forwarded-For` gravada pelo proxy da plataforma, e não do que o cliente envia.
  - **Configuração:** `TRUSTED_PROXY_HOPS=1` no `render.yaml`. O app usa a N-ésima entrada **da direita** (`app/core/client_ip.py`), que é a que o proxy do Render acrescentou. Isso funciona tanto se o proxy acrescenta ao header quanto se o sobrescreve.
  - **Por que não `uvicorn --proxy-headers --forwarded-allow-ips='*'`**, como se planejou: com `'*'`, o uvicorn (0.54) usa a entrada mais à **esquerda**, que é controlada pelo cliente. Bastaria mandar um `X-Forwarded-For` falso diferente a cada tentativa para fugir do limite do login. Também não dá para listar os IPs dos proxies, porque o Render não os publica. Por isso o container roda com `--no-proxy-headers`, e nenhum código usa um IP forjável por engano.
  - **Pressuposto:** no Render, o serviço só é acessível pelo proxy da plataforma, então sempre existe exatamente um proxy na frente. Se a topologia mudar (por exemplo, com um CDN na frente), ajuste `TRUSTED_PROXY_HOPS`.
  - **Verificação:** na imagem local com `TRUSTED_PROXY_HOPS=1`, 6 tentativas com a parte esquerda forjada (um IP diferente a cada vez) e o mesmo IP real deram 429 na sexta. Seis IPs reais diferentes não foram bloqueados.
- **Para escalar** além de uma instância, trocar o armazenamento por um compartilhado (por exemplo, Redis com contadores atômicos). A interface `RateLimiter.hit(key)` isola essa troca.
