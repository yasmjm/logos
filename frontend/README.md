# Logos · Frontend

Interface da central de incidentes: React + Vite + TypeScript, TanStack Query, Tailwind e shadcn/ui.

## Rodar localmente

Pré-requisitos: Node 24+ e pnpm (`corepack enable` instala a versão do `packageManager`).

```bash
# 1. backend (outro terminal), a partir da raiz do repositório
docker compose up -d
cd backend && uv run uvicorn app.main:app --reload --port 8000

# 2. frontend
cd frontend
cp .env.example .env.local   # VITE_API_URL=http://localhost:8000
pnpm install
pnpm dev                     # http://localhost:5173
```

O CORS do backend já libera `http://localhost:5173` por padrão (`FRONTEND_ORIGINS`).
Entre com **Entrar como Ana** ou **Entrar como Bruno** (senha de demonstração `logos123`).

## Scripts

| Comando | O que faz |
|---|---|
| `pnpm dev` | servidor de desenvolvimento com HMR |
| `pnpm lint` | oxlint (avisos também falham) |
| `pnpm typecheck` | `tsc -b` em modo strict |
| `pnpm build` | typecheck + build de produção em `dist/` |

`VITE_API_URL` é obrigatório no build de produção (por exemplo, a URL do backend no Render).

## Estrutura

- `src/api/`: cliente HTTP, sessão, erros (`ApiError`), política de retry e tipos que espelham os schemas da API.
- `src/lib/labels.ts`: **todos** os rótulos de status, categoria, criticidade e origem.
- `src/index.css`: tokens de design (tema escuro padrão e tema claro).
- `src/components/ui/`: componentes gerados pelo shadcn; `src/components/`: componentes do domínio.
- `src/features/`: telas (login, shell).
