# ADR 0003: Polling de 5 s em vez de SSE ou WebSocket

- **Status:** aceito
- **Data:** 2026-10-21

## Contexto

A fila precisa refletir incidentes novos e mudanças de outros analistas, como "Bruno assumiu". O escopo é uma central com poucos analistas simultâneos, uma única instância da API (Render Starter) e banco no Neon. WebSocket e SSE estão fora do escopo do MVP (CLAUDE.md).

## Alternativas consideradas

1. **Polling de 5 s** com TanStack Query: fila, indicadores, métricas e o incidente aberto.
2. **SSE** (Server-Sent Events): o servidor empurra eventos pela mesma conexão HTTP.
3. **WebSocket**: canal bidirecional.

## Decisão

Polling de 5 s, que pausa com a aba oculta.

- **Basta para o caso:** um atraso de até 5 s é aceitável para a triagem. O que não pode acontecer é uma ação ser aplicada sobre um estado velho, e isso o **lock otimista** já impede: quem age sobre um dado desatualizado recebe 409 com o estado atual, por mais "ao vivo" que a tela esteja.
- **Simples e robusto:** são requisições HTTP comuns, que passam pelo mesmo cache, retry, `Retry-After`, autenticação e CORS do resto da API. Nada de reconexão, heartbeat ou estado de conexão no servidor. Uma queda da API vira o aviso "Mostrando os dados de há X s", e a fila não perde o que já mostrava.
- **Funciona com várias instâncias sem infraestrutura nova:** cada requisição lê o banco, então não há estado compartilhado a sincronizar entre instâncias.
- **Custo aceitável:** para cada analista, são cerca de 4 consultas leves a cada 5 s (fila de até 200 itens, summary, contagem, métricas), servidas pelo índice parcial da migration `0004`. A pausa com a aba oculta corta o tráfego de abas esquecidas.

## Quando migrar

Vale trocar para push quando pelo menos um destes casos aparecer:

- **Volume:** dezenas de analistas ou um volume de incidentes em que 5 s de atraso, ou o custo das consultas repetidas, passe a importar;
- **Latência:** uma exigência de reação abaixo de poucos segundos;
- **Escala horizontal:** várias instâncias da API.

**Caminho recomendado:** **SSE** apenas para notificações (o cliente continua escrevendo via HTTP, com lock otimista), com **Redis pub/sub** entre as instâncias. Cada escrita publica `incident.changed {id, version}`; cada instância repassa o evento aos seus clientes SSE, que invalidam as queries afetadas no TanStack Query. O polling fica como fallback, mais espaçado, para quando a conexão SSE cair. WebSocket só se surgir uma necessidade real de comunicação bidirecional.
