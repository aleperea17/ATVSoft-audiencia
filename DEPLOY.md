# Deploy — ATV Audiencia

VPS Ubuntu 24, IP `72.60.244.220`, dominio `audiencia.atvos.io`.
Cada bloque es un comando. Correrlos de a uno, en este orden.
Docker, Nginx y Certbot tienen que estar instalados (el resto de los módulos ATV ya los usa).

El repo es privado. En el VPS hace falta una deploy key o una sesión de GitHub con acceso de lectura.

## 1. Puertos

```bash
ss -tlnp | grep -E ':8020|:3020'
```

Si no imprime nada, 8020 y 3020 están libres. Si imprime una línea, ese puerto está ocupado y no hay que seguir.

## 2. Clonar

```bash
git clone https://github.com/aleperea17/atv-audiencia.git /opt/atv-audiencia
```

```bash
cd /opt/atv-audiencia
```

## 3. `.env`

Generar la clave de Postgres en el VPS:

```bash
openssl rand -hex 32
```

Buscar el secreto de sesión que ya usan los otros módulos. Tiene que ser el mismo valor, no uno nuevo:

```bash
grep -R --include=.env -n ECOSYSTEM_SESSION_SECRET /opt
```

Crear `/opt/atv-audiencia/.env` con estos valores:

| Variable | De dónde sale |
| --- | --- |
| `POSTGRES_DB` | `audiencia` |
| `POSTGRES_USER` | `audiencia` |
| `POSTGRES_PASSWORD` | el hex del `openssl` de arriba |
| `DB_HOST` | `audiencia-db` (el compose igual lo fuerza) |
| `ECOSYSTEM_SESSION_SECRET` | el mismo secreto que el resto de los módulos, el del `grep`. Mínimo 32 caracteres. Si es otro, la cookie no valida |
| `IG_ACCESS_TOKEN` | el token de larga duración ya conectado a @juanxcarrizo. No está en el repo |
| `IG_USER_ID` | `17841400159563968` |
| `IG_GRAPH_VERSION` | `v25.0` |
| `ANTHROPIC_API_KEY` | la key de Anthropic. Sin ella el contenedor no clasifica |
| `CLAUDE_BIN` | `claude` |
| `CORS_ORIGINS` | `https://audiencia.atvos.io` |
| `BACKEND_PORT` | `8020` |
| `FRONTEND_PORT` | `3020` |
| `PIPELINE_MAX_REELS` | `5`. Borrar la línea procesa todos los reels |
| `PIPELINE_MAX_PERFILES` | `50`. Borrar la línea enriquece y clasifica todos los perfiles nuevos |
| `DISCORD_WEBHOOK_URL` | webhook de Discord, o vacío. Vacío = el aviso de vencimiento solo queda en el log |

```bash
nano /opt/atv-audiencia/.env
```

## 4. Contenedores

```bash
cd /opt/atv-audiencia && docker compose up -d --build
```

```bash
cd /opt/atv-audiencia && docker compose ps
```

Los tres tienen que quedar en marcha: `audiencia-db`, `audiencia-backend`, `audiencia-frontend`.

## 5. Nginx

Copia el archivo. No uses `ln -s`.

```bash
cp /opt/atv-audiencia/nginx/audiencia.atvos.io.conf /etc/nginx/sites-enabled/audiencia.atvos.io
```

```bash
nginx -t
```

```bash
systemctl reload nginx
```

## 6. SSL

El DNS de `audiencia.atvos.io` tiene que apuntar a `72.60.244.220` antes de pedir el certificado.

```bash
getent hosts audiencia.atvos.io
```

```bash
certbot --nginx -d audiencia.atvos.io
```

## 7. Backup a las 4 AM

```bash
chmod +x /opt/atv-audiencia/scripts/backup.sh
```

```bash
(crontab -l 2>/dev/null; echo '0 4 * * * /opt/atv-audiencia/scripts/backup.sh >> /var/log/atv-audiencia-backup.log 2>&1') | crontab -
```

El script vuelca la base con `pg_dump` dentro de `audiencia-db` y borra los `.sql.gz` de más de 14 días en `/opt/atv-audiencia/backups`.

## 8. Verificación

```bash
curl -fsS http://127.0.0.1:8020/api/health
```

```bash
curl -fsS https://audiencia.atvos.io/api/health
```

```bash
docker exec audiencia-backend python scripts/test_ig.py
```

```bash
docker exec audiencia-backend python -m src.pipeline_runner run-once
```

`/api/health` no pide cookie. El resto de la API sí.

## 9. Redeploy

```bash
cd /opt/atv-audiencia && git pull && docker compose up -d --build
```

## Cookie `ecosystem_session`

Este módulo no emite la cookie. Solo la verifica.

Para que el browser la mande a `https://audiencia.atvos.io`:

- El login del ecosistema tiene que setearla con `Domain=.atvos.io` (con el punto). Una cookie de host de otro subdominio no llega.
- `ECOSYSTEM_SESSION_SECRET` en este `.env` tiene que ser el mismo string que en los otros módulos. La firma es HMAC-SHA256 del payload.
- El valor es `payload_b64.sig_b64`. El JSON incluye `exp` en unix UTC.
- Con el sitio en `audiencia.atvos.io` y la API en el mismo host (`/api` vía Nginx), la cookie viaja en las peticiones same-origin. `SameSite=Lax` alcanza.

Si el secreto no coincide, la API responde 401. `/api/health` sigue respondiendo igual.
