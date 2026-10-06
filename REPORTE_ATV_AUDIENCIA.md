# ATV Audiencia

Módulo que, por cada reel de la cuenta de Instagram del cliente, calcula qué porcentaje de quienes interactuaron son leads calificados y muestra esa lista. La carga es automática. A mano solo se conecta Instagram (token en el entorno) y se edita la rúbrica (`PUT /api/rubrica`).

## Qué quedó armado

- Job cada 30 minutos (APScheduler) que hace upsert de reels por `ig_media_id`, trae comentarios y enriquece perfiles nuevos con Business Discovery.
- Webhook `POST /api/webhooks/manychat` (username + keyword) que crea la interacción y es idempotente.
- Un perfil se clasifica una sola vez con Claude CLI (`claude -p … --output-format json`, sin SDK) y se reutiliza en todos los reels. Se vuelve a clasificar si pasaron más de 30 días.
- Si Business Discovery no puede leer la cuenta, el perfil se guarda igual con avatar `sin_datos` y `calificado=false`, sin llamar a Claude.
- API de reels, preview y listado paginado de calificados, y lectura/edición de la rúbrica.
- Frontend con dos vistas: la grilla principal y “Ver todos”.
- Auth local de la cookie `ecosystem_session` (HMAC-SHA256). Este módulo no la emite.
- Postgres 18 en el mismo compose (`audiencia-db`), sin puerto publicado. Las tablas viven en el schema `audiencia` y las crea Pony con `generate_mapping(create_tables=True)`.

El porcentaje es `calificados / interacciones` del reel. Si no hay interacciones, es 0.

## Estructura

```text
docker-compose.yml
.env.example
nginx/audiencia.atvos.io.conf
scripts/backup.sh
REPORTE_ATV_AUDIENCIA.md
backend/
  main.py
  requirements.txt
  Dockerfile
  scripts/mint_session.py
  src/
    db.py models.py schemas.py auth.py
    metrics.py keyword_match.py classification_json.py graph_errors.py
    controllers/   reels, rubrica, webhook, health
    services/      reels, rubrica, webhook, pipeline, instagram, graph, classification
frontend/
  index.html vite.config.js package.json Dockerfile nginx-spa.conf
  src/           App.jsx, api.js, CSS Modules
```

Tablas en `audiencia`: `reel`, `interaccion`, `perfil`, `clasificacion`, `rubrica`.

Dos piezas operativas que no se muestran en la UI: `reel.comentarios_sync_at` y la tabla `estado_sync` (cursor del backfill). Se crean con `ADD COLUMN IF NOT EXISTS` / `CREATE SCHEMA IF NOT EXISTS`. Las columnas nuevas llevan `DEFAULT` cuando el tipo lo permite (`calificado` false, `score` 0).

## Permisos de Meta

Token de larga duración de la cuenta profesional (Facebook Login / Page token) y el Instagram Business Account ID en `IG_USER_ID`.

Para leer reels, comentarios y Business Discovery hacen falta:

- `instagram_basic`
- `instagram_manage_comments` (edge `/{media-id}/comments`)
- `pages_read_engagement`
- `instagram_manage_insights` (lo pide la doc actual de Business Discovery)
- `pages_show_list` (para ubicar la cuenta de Instagram vinculada a la página al hacer el setup)

Si el rol de la página se dio desde Business Manager, la doc de Business Discovery del 12 de agosto de 2026 pide además uno de estos:

- `ads_management`
- `ads_read`

`business_management` no figura en esa página. Sigue siendo el permiso habitual para listar activos del Business Manager; no reemplaza a `ads_management` / `ads_read` en esa llamada.

Graph API usada: `v25.0`, la misma que el resto de ATV. Se puede cambiar con `IG_GRAPH_VERSION`.

## Verificado en Business Discovery

No. El nodo IG User (Graph API v26) no tiene `is_verified` ni otro campo de tilde entre los campos públicos. Business Discovery solo puede pedir esos campos públicos.

El código igual pide `is_verified` una vez. Si la API lo rechaza o no lo manda, deja `verificado = null` y no lo vuelve a pedir en el proceso. No hay scraping.

Con `verificado` en null la rúbrica no se cumple (hace falta cuenta verificada), así que `calificado` queda en false. Cuando Meta exponga el campo, el mismo código lo va a guardar.

La cuenta propia respondió en la Graph API. `is_verified` no se probó contra una cuenta ajena: la doc del nodo no lo incluye y, sin un perfil de terceros, no hay respuesta que mostrar.

## Variables de entorno

Van en `.env` en la raíz (el compose las inyecta). Los secretos no tienen valor de ejemplo: generarlos con `openssl rand -hex 32`.

| Variable | Uso |
| --- | --- |
| `POSTGRES_DB` | Nombre de la base. Valor `audiencia`. |
| `POSTGRES_USER` | Usuario. Valor `audiencia`. |
| `POSTGRES_PASSWORD` | Clave de Postgres. Generarla; el ejemplo queda vacío. |
| `DB_HOST` | `audiencia-db` (nombre del servicio en la red de Docker). |
| `ECOSYSTEM_SESSION_SECRET` | Clave HMAC de la cookie. Mínimo 32 caracteres. El proceso no arranca si falta. |
| `MANYCHAT_WEBHOOK_TOKEN` | Token del webhook. Header `X-Webhook-Token` o `Authorization: Bearer`. Mínimo 16 caracteres. |
| `IG_ACCESS_TOKEN` | Token de la cuenta profesional |
| `IG_USER_ID` | Instagram Business Account ID |
| `IG_GRAPH_VERSION` | Default `v25.0` |
| `ANTHROPIC_API_KEY` | La usa el CLI dentro del contenedor. Si está vacía, el CLI tiene que tener sesión propia. |
| `CLAUDE_BIN` | Default `claude` |
| `CORS_ORIGINS` | En producción, `https://audiencia.atvos.io`. Same-origin vía Nginx no depende de CORS. |
| `BACKEND_PORT` | Host. Default `8020` |
| `FRONTEND_PORT` | Host. Default `3020` |

Cookie que verifica el backend:

```text
ecosystem_session = <payload_b64>.<sig_b64>
```

`payload_b64` es el JSON en base64 url-safe sin padding. Tiene que traer `exp` (unix UTC). `sig_b64` es HMAC-SHA256 de los bytes de `payload_b64`, con `ECOSYSTEM_SESSION_SECRET`, también en base64 url-safe sin padding. Hay 60 segundos de tolerancia. `backend/scripts/mint_session.py` imprime una cookie de prueba.

La cookie la tiene que setear el login del ecosistema en `.atvos.io` para que el browser la mande a `audiencia.atvos.io`.

## Deploy en el VPS

Mismo patrón que `/opt/atv-clients`: compose en el host, Nginx del sistema adelante.

1. Clonar el repo en `/opt/atv-audiencia`.
2. `cp .env.example .env` y completar. `POSTGRES_PASSWORD`, `ECOSYSTEM_SESSION_SECRET` y `MANYCHAT_WEBHOOK_TOKEN` se generan así:

   ```bash
   openssl rand -hex 32
   ```

3. `docker compose up -d --build` desde `/opt/atv-audiencia`. Postgres no publica el 5432: solo el backend lo ve como `audiencia-db`. El volumen es `audiencia-pgdata`, montado en `/var/lib/postgresql`.
4. Backup diario. `chmod +x /opt/atv-audiencia/scripts/backup.sh` y esta línea de cron, a las 4 AM:

   ```cron
   0 4 * * * /opt/atv-audiencia/scripts/backup.sh >> /var/log/atv-audiencia-backup.log 2>&1
   ```

   El script corre `pg_dump` dentro de `audiencia-db`, guarda `/opt/atv-audiencia/backups/audiencia_FECHA.sql.gz` y borra los de más de 14 días.
5. Copiar `nginx/audiencia.atvos.io.conf` a `/etc/nginx/sites-available/audiencia.atvos.io` y habilitar el sitio. Los puertos `8020` y `3020` tienen que coincidir con `BACKEND_PORT` y `FRONTEND_PORT`.
6. `nginx -t && systemctl reload nginx`.
7. Certificado: `certbot --nginx -d audiencia.atvos.io`.
8. En el server de Nginx, el `location /api/webhooks/` (y también `/api/`) usa `proxy_pass http://127.0.0.1:8020;` **sin path**. Así `/api/webhooks/manychat` llega al backend con el mismo path. Un `proxy_pass` con barra final borra el prefijo y el webhook responde 404.
9. ManyChat pega a `https://audiencia.atvos.io/api/webhooks/manychat` con el token y un JSON `{ "username": "…", "keyword": "…" }`. También acepta `ig_username`.

El contenedor del backend instala Claude Code CLI, igual que Report Calls. La primera corrida del job arranca al levantar el proceso y después cada 30 minutos. Si faltan el token o el user id de Instagram, el proceso igual levanta y la pantalla queda vacía hasta configurarlos.

## Decisiones y supuestos

- El estilo sale de ATV-MKT (`frontend/src/app/globals.css`): fondo `#050505`, cards `#0C0C0E`, acento `#E63946`, Inter, borde y hover de 150 ms. Esas variables ganan sobre `#0D0D0D` y `#FF3B30` del brief.
- No hay pantalla para conectar Instagram ni para editar la rúbrica. La rúbrica inicial queda seedeada y se cambia por `PUT /api/rubrica`. El texto inicial es el del brief.
- La keyword de ManyChat se mapea así: primero un reel que ya tenga esa keyword (gana el más reciente); si ninguno, el reel más reciente cuya caption la contiene como palabra y que todavía no tiene keyword. En ese caso se le guarda la keyword. Si no hay match, el webhook responde 404.
- `UNIQUE (reel_id, ig_username)`. Si la persona comenta y además entra por ManyChat, queda el primer origen.
- Usernames guardados en minúsculas.
- La compuerta de la rúbrica obliga `calificado=false` si `verificado` no es `true` o si el avatar no es `infoproductor` ni `growth_operator`. No fuerza el `true` si el modelo dijo `false`.
- JSON inválido de Claude: un reintento y, si falla, se loguea y el perfil sigue sin clasificar para la próxima corrida.
- Rate limit: códigos 4, 17, 32, 613 y también 80002 (el que Meta documenta como “demasiadas llamadas a esta cuenta de Instagram”), más HTTP 429. Backoff 2, 4, 8… segundos, y la corrida corta esa fase. El upsert es idempotente, así que la siguiente retoma.
- Con el historial ya cargado, cada corrida refresca las dos primeras páginas de media (los reels nuevos) y comentarios de los 15 reels menos sincronizados. El primer backfill avanza de a 4 páginas por corrida.
- Lotes por corrida: 12 enriquecimientos y 8 clasificaciones.
- No hay sidebar, KPIs extra, export, setters ni filtros.
- Las llamadas HTTP a Graph y el subprocess de Claude corren en `asyncio.to_thread`. Las queries de Pony no usan lambdas: `.select()[:]` y filtro en Python, o `.get()`.

## Pendiente

- Probar Business Discovery con un token real y confirmar en logs si `is_verified` viene, se omite o la API lo rechaza.
- Alinear el login del ecosistema con el formato de cookie de arriba.
- Cargar en el VPS `IG_ACCESS_TOKEN`, `IG_USER_ID`, `POSTGRES_PASSWORD` y los secretos de sesión y de ManyChat.
- En esta máquina no hay Docker, así que no se levantó el compose. Sí corrieron los tests de HMAC, rúbrica, keyword, rate limit y el `proxy_pass` de Nginx (`6 passed`), el build de Vite, y las dos vistas en el browser.
