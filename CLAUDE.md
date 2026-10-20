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

## Fora do escopo do MVP
Integração real com WhatsApp, mapa, WebSocket/SSE (usamos polling), app do motorista.
