# MPCARS2 - Sistema de Aluguel de Veiculos

Sistema completo de gestao para locadora de veiculos com PWA mobile.

## Stack

| Componente | Tecnologia |
|------------|------------|
| Backend | FastAPI 0.115.6 + SQLAlchemy 2.0.36 + Alembic + Pydantic v2 |
| Frontend | React 18 + TypeScript + Vite 6 + TanStack Query v5 + Tailwind CSS |
| Database | PostgreSQL 16 + PgBouncer |
| Cache | Redis 7 |
| Tasks | Celery (alertas, backups, manutencao) |
| Infra | Docker Compose + Nginx reverse proxy |
| PWA | vite-plugin-pwa + Workbox (instalavel iOS/Android) |

## Funcionalidades

### 18 Paginas Completas
- **Dashboard** - KPIs em tempo real, graficos, alertas, agenda, top 5 clientes/veiculos
- **Contratos** - Locacao PF e PJ/empresa, NF por periodo, encerramento, pagamentos parciais
- **Veiculos** - Frota com fotos, status, KM, historico financeiro por veiculo
- **Clientes** - PF e PJ, cadastro completo com validacao CPF/CNPJ
- **Empresas** - Cadastro com auto-criacao de cliente PJ, frotas vinculadas
- **Financeiro** - Receitas, despesas, filtros por tipo/status/categoria/veiculo/periodo, export Excel/PDF/CSV
- **Seguros** - Apolices, parcelas, vencimentos
- **IPVA/Licenciamento** - Parcelas, pagamentos, sync status
- **Multas** - Infracoes, vencimentos, prevencao pagamento duplo
- **Manutencoes** - Preventivas, corretivas, alertas por KM/data
- **Reservas** - Agendamentos com status do veiculo
- **Relatorios** - NF empresa, historico por veiculo, PDF
- **Despesas Loja** - Custos operacionais fora dos contratos
- **Configuracoes** - Perfil, senha
- **Usuarios** - Gestao de perfis e permissoes (admin only)
- **Governanca/Backups** - Backup/restore, versao, commits recentes

### PWA Mobile
- Instalavel como app nativo no celular (iOS e Android)
- Bottom navigation bar com 5 itens (Inicio, Veiculos, Contratos, Financeiro, Mais)
- Cards mobile em todas as paginas de listagem (sem scroll horizontal)
- Modais responsivos em bottom-sheet
- Service worker com cache de assets
- Prompt de instalacao automatico

### Seguranca
- Rate limiting global (200/min, 20/sec)
- LIKE wildcard escape em todas as queries
- XSS: strip_html() em inputs de texto
- Token JWT com expiracao de 2h
- Validacao de valores em todos os endpoints financeiros
- Perfil default "operador" (principio do menor privilegio)
- PCI compliance (sem armazenamento de dados de cartao)

### Performance
- 34 indexes otimizados no banco
- Dashboard com cache Redis
- Lazy loading de todas as paginas (React.lazy + Suspense)
- Code splitting por pagina (Vite manual chunks)
- Nginx gzip + cache 1 ano para assets estaticos

## Estrutura do Projeto

```
mpcars2/
├── backend/
│   ├── app/
│   │   ├── core/           # Config, database, security, deps, cache, validators
│   │   ├── models/         # SQLAlchemy models (32 tabelas)
│   │   ├── routers/        # 16 routers FastAPI (130+ endpoints)
│   │   ├── schemas/        # Pydantic schemas (contratos)
│   │   ├── services/       # Logica de negocio (contratos, export, pdf)
│   │   └── tasks/          # Celery (alertas, backup, manutencao)
│   ├── alembic/            # Migrations
│   └── tests/              # 24 testes automatizados
├── frontend/
│   ├── public/             # PWA icons (SVG + PNG)
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/     # AppLayout, Sidebar, Header, BottomNav, MoreSheet
│   │   │   ├── onboarding/ # FirstUseGuide, ContextualTips
│   │   │   └── shared/     # DataTable, StatusBadge, PWAInstallPrompt, etc
│   │   ├── config/         # Navigation config
│   │   ├── contexts/       # Auth, Config, Sidebar
│   │   ├── hooks/          # useDebounce
│   │   ├── pages/          # 18 paginas
│   │   ├── services/       # API client (axios + interceptors)
│   │   └── types/          # TypeScript interfaces
│   ├── vite.config.ts      # Vite + PWA plugin
│   └── nginx.conf          # Nginx para SPA + PWA
├── nginx/                  # Reverse proxy config
├── docker-compose.yml      # Desenvolvimento
└── docker-compose.prod.yml # Producao
```

## Deploy

```bash
# Backend
cd /docker/mpcars2
docker build -t mpcars2-api-fixed ./backend
docker stop mpcars2-api mpcars2-celery && docker rm mpcars2-api mpcars2-celery
docker run -d --name mpcars2-api --restart always --network mpcars2_default \
  --env-file .env -p 8002:8000 \
  -v mpcars2_uploads:/app/uploads -v mpcars2_pdfs:/app/pdfs \
  -v /docker/mpcars2/backups:/backups -v /docker/mpcars2/secrets:/run/secrets:ro \
  mpcars2-api-fixed
docker run -d --name mpcars2-celery --restart always --network mpcars2_default \
  --env-file .env \
  -v /docker/mpcars2/backups:/backups -v /docker/mpcars2/secrets:/run/secrets:ro \
  mpcars2-api-fixed celery -A app.celery_app worker -l info -B --concurrency=4

# Frontend
cd frontend
docker run --rm -v "$(pwd)":/app -w /app node:20-alpine sh -c 'npm ci && npm run build'
docker cp dist/. mpcars2-web:/usr/share/nginx/html/
docker cp nginx.conf mpcars2-web:/etc/nginx/conf.d/default.conf
docker exec mpcars2-web nginx -s reload
```

## Backup

- Systemd timer: diario as 03:30 UTC em /var/backups/mpcars2/
- Celery: backup diario (configuravel)
- Google Drive: sync automatico para pasta MPCARS Backups
- Manual: `docker exec mpcars2-db pg_dump -U mpcars2 -d mpcars2 | gzip > backup.sql.gz`

## Versao

**v2.0.0** - Sistema completo com 18 paginas, 130+ endpoints, PWA mobile, 135+ melhorias implementadas.

## Licenca

Proprietary - MPCARS. Todos os direitos reservados.
