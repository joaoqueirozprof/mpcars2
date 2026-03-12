# Operacao de Producao

## Antes do go-live

1. Copie `.env.production.example` para `.env.production`.
2. Troque `POSTGRES_PASSWORD`, `DATABASE_URL`, `SECRET_KEY` e credenciais do pgAdmin.
3. Ajuste `CORS_ORIGINS` e `TRUSTED_HOSTS` com o dominio real.
4. Defina:
   - `ENVIRONMENT=production`
   - `ENABLE_API_DOCS=false`
   - `SEED_ON_STARTUP=false`
   - `RUN_LEGACY_COLUMN_MIGRATIONS=false`
   - `BACKUP_ENABLED=true`
   - `BACKUP_DIRECTORY` apontando para um drive dedicado da VPS
5. Suba a producao com:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production up -d --build
```

## Backup recomendado

Rode o script abaixo pelo menos 1 vez por dia:

```bash
./ops/backup_mpcars2.sh
```

Ele salva:
- `database.sql`
- `assets.tar.gz` com `uploads` e `pdfs`
- `manifest.txt`

Sugestao de cron:

```bash
0 2 * * * cd /docker/mpcars2 && ./ops/backup_mpcars2.sh >> /var/log/mpcars2-backup.log 2>&1
```

## Governanca de acesso

- O painel `/backups` fica reservado a `admin` e `owner`.
- O perfil `owner` enxerga apenas backups e nao acessa dados operacionais.
- A area de usuarios e versoes permanece exclusiva do `admin`.
- Recuperacao de senha deve ser feita por link temporario gerado pelo admin, sem definir a senha final do usuario.

## Restore

Para restaurar um backup:

```bash
./ops/restore_mpcars2.sh /caminho/do/backup
```

## Checklist rapido

- Nao deixar `SECRET_KEY` padrao.
- Nao deixar senha do banco padrao.
- Nao expor `/docs` em producao.
- Nao manter `SEED_ON_STARTUP=true` com dados reais.
- Usar backup diario com retencao.
- Restringir dominios em `CORS_ORIGINS` e `TRUSTED_HOSTS`.
- Subir `pgAdmin` so quando precisar:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.production --profile admin up -d mpcars2-pgadmin
```
