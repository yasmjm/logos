# Logos — Central de Resposta a Incidentes

## Contexto
MVP para o case técnico da AutoU. Analistas da central de uma transportadora
(5.000 caminhões) fazem a triagem de incidentes sob pressão.
Problema central: a central reage devagar porque a informação chega espalhada,
sem prioridade e sem dono definido.

## Stack
- backend/: Python 3.12, FastAPI, SQLAlchemy 2 (sync), Alembic, Pydantic v2, PostgreSQL, pytest, uv
- frontend/: React + Vite + TypeScript, TanStack Query, Tailwind, shadcn/ui

## Regras de domínio
- Categorias: vehicle_accident, accident_with_victims, adverse_weather, mechanical_failure, road_blockage
- Criticidade: high, medium, low
- Status: open, investigating, closed, inconclusive
- Transições válidas: open→investigating; investigating→closed|inconclusive|open; closed|inconclusive→open (reabrir)
- Ao entrar em investigating, assigned_to recebe o analista que fez a ação.
- Toda mudança de status usa optimistic locking: o cliente envia a version que viu;
  o UPDATE filtra por id E version; nenhuma linha afetada → 409 com o estado atual.
  NUNCA usar check-then-act (SELECT e depois UPDATE).
- Toda mudança de status gera um registro em incident_events.

## Convenções
- Código, identificadores e commits em inglês (Conventional Commits). README e docs em português.
- Commits pequenos, um por mudança lógica. Commits só com aprovação explícita da Yasmim: antes de comitar, mostre o resumo do diff e a mensagem proposta e espere o ok.
- Antes de implementar algo não trivial, explicar a abordagem em 3 a 5 linhas e esperar o ok.
- Não adicionar dependências sem justificar.

## Convenções do frontend
- pnpm (versão fixada em `packageManager`). Antes de commitar: `pnpm lint`, `pnpm typecheck` e `pnpm build` em `frontend/`.
- Textos da interface em português; código e identificadores em inglês.
- Rótulos de status, categoria, criticidade e origem vêm **só** de `src/lib/labels.ts` (status e categorias exatamente como no case). Nunca escrever esses textos nos componentes.
- Cores, espaçamento e tipografia vêm dos tokens em `src/index.css` (CSS variables, tema escuro padrão + claro). Nada de cores soltas nos componentes; o `--accent` é neutro e nunca compete com a criticidade.
- Criticidade nunca só por cor: sempre cor + ícone + rótulo (`SeverityBadge`). Status também com ícone + rótulo (`StatusBadge`).
- Incidente com responsável: estilo `.incident-assigned` + `AssigneeBadge` (iniciais do analista).
- Toda chamada à API passa por `src/api/client.ts` (`apiRequest`), que trata o token, o 401 (encerra a sessão: "Sua sessão expirou") e transforma problem+json em `ApiError`. O 409 traz o estado atual em `error.current`.
- Retry (TanStack Query): nunca em 4xx; só falha de rede e 502/503/504, até 3 vezes, respeitando o `Retry-After`.
- Tipos da API em `src/api/types.ts`, espelhando os schemas do backend; mudou um schema, atualize os tipos no mesmo PR.
- Token JWT em memória + sessionStorage (por aba). Preferências (tema) no localStorage, sempre com try/catch (`src/lib/storage.ts`).
- Componentes do shadcn só quando necessários (`pnpm dlx shadcn@latest add <nome>`); ficam em `src/components/ui/`.
- Acessibilidade: foco visível, `aria-label` em botões só com ícone, `prefers-reduced-motion` respeitado.

## Fora do escopo do MVP
Integração real com WhatsApp, mapa, WebSocket/SSE (usamos polling), app do motorista.
