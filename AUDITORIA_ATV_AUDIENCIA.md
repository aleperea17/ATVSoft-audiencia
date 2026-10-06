# Auditoría ATV Audiencia

Revisión de solo lectura hecha el 6 de octubre de 2026 en esta máquina (`c:\Users\aledl\Desktop\ATV-Audiencia`). No se modificó código, configuración ni datos.

## 1. Resumen ejecutivo

**Estado: Parcial.**

El código del módulo está escrito y el token de Instagram es válido: la Graph API lista reels de @juanxcarrizo y Business Discovery responde. El sistema no está operativo. No hay repositorio git, Docker no está instalado, Postgres no corre, no hay tablas con datos, el pipeline no se ejecutó nunca y no hay clasificaciones. Aunque se desplegara hoy, la compuerta de la rúbrica dejaría `calificado=false` en todos los perfiles, porque Business Discovery rechaza el campo `is_verified`.

## 2. Resultado por sección

| Sección | Estado | Nota |
| --- | --- | --- |
| 1. Estructura y stack | ✅ OK | FastAPI + Pony, React + Vite + CSS Modules. Sin TypeScript ni Tailwind en el código de la app. |
| 2. Seguridad | ⚠️ Warning | No hay secretos en el código. `.env` está en `.gitignore`, pero no existe repo git. El webhook no usa la cookie de sesión. |
| 3. Base de datos | ❌ Error | El compose declara Postgres 18 bien. No está corriendo, no hay filas, no hay cron ni backups. |
| 4. Instagram | ⚠️ Warning | Token válido. Faltan scopes pedidos. Comentarios de un reel propio respondieron 200 igual. No hay job de renovación ni `scripts/test_ig.py`. |
| 5. Pipeline | ❌ Error | El job está programado en código cada 30 min. Nunca corrió. `is_verified` no existe en la API. |
| 6. Clasificación | ❌ Error | Claude CLI está definido, no instalado acá, y no hay clasificaciones. |
| 7. API y métricas | ⚠️ Warning | Endpoints definidos. No hay un reel en base para contrastar el porcentaje. |
| 8. Frontend | ✅ OK | Las dos vistas están. El botón del % se probó antes contra una API de humo, no contra datos reales. |
| 9. Deploy | ❌ Error | Sin contenedores, sin Nginx instalado, sin SSL y sin commit para comparar con un VPS. |

## 3. Problemas por gravedad

### Críticos

1. **El proceso no está levantado.** `docker` no existe en esta máquina. `docker compose ps` no se pudo ejecutar. No hay contenedores `audiencia-db`, `audiencia-backend` ni `audiencia-frontend`.
   - Solución: instalar Docker en el VPS, completar `.env` y correr `docker compose up -d --build` desde `/opt/atv-audiencia`.

2. **No hay base ni datos.** Sin Postgres no hay schema `audiencia`, ni conteos, ni logs de corrida, ni clasificaciones. Los UNIQUE están declarados en Pony (`reel.ig_media_id`, `composite_key(reel, ig_username)`, `perfil.ig_username`, `clasificacion.perfil` unique) y no se pudieron verificar en el servidor.
   - Solución: después del `up`, consultar `information_schema` y `\d audiencia.*` dentro de `audiencia-db`.

3. **Nadie puede quedar calificado con la API actual.** Business Discovery respondió `(#100) Tried accessing nonexisting field (is_verified)`. El código, si el campo no viene, guarda `verificado=null` y `apply_rubric_gate` fuerza `calificado=false` salvo que `verificado` sea `true`.
   - Solución: mientras Meta no entregue el tilde, no usar `verificado is True` como compuerta obligatoria. Dejar que el modelo decida con bio, web y captions, y guardar `verificado=null`.

4. **No hay deploy ni git.** Esta carpeta no es un repositorio (`fatal: not a git repository`). No hay commit, no hay remoto y no hay forma de saber si un VPS coincide con “el último commit”. Nginx del repo escucha solo el puerto 80, sin certificado.
   - Solución: `git init`, commit sin `.env`, push, clonar en el VPS y emitir el certificado con certbot. El `proxy_pass` de `/api/` ya apunta al backend sin recortar el path.

### Altos

5. **No existe `scripts/test_ig.py`.** No se pudo ejecutar. El chequeo equivalente, hecho a mano contra Graph y sin escribir en la base, está en la sección 4.
   - Solución: agregar ese script como lectura de `debug_token` + un reel + Business Discovery, sin persistir.

6. **No hay renovación de token ni tabla `ig_token`.** El token se lee solo de `IG_ACCESS_TOKEN` en el entorno. `debug_token` dice `expires_at: 0` (el token no vence) y `data_access_expires_at` el 2 de diciembre de 2026. El JSON que se pegó en el chat decía vencimiento el 2 de noviembre de 2026; Graph no coincide con esa fecha.
   - Solución: si más adelante el token pasa a tener vencimiento, guardar `ig_token` y un job que lo refresque antes de `data_access_expires_at`. Hoy no hace falta un refresh del token en sí.

7. **Faltan scopes respecto de la lista pedida.** Concedidos: `instagram_basic`, `instagram_manage_insights`, `pages_read_engagement`, `pages_show_list`, `instagram_manage_messages`, `public_profile`. No están `instagram_manage_comments` ni `business_management`. Aun así, `GET /{media-id}/comments?fields=username&limit=1` devolvió HTTP 200. Business Discovery de campos públicos también devolvió 200 sin `business_management`.
   - Solución: pedir `instagram_manage_comments` en la app de Meta antes de paginar comentarios en producción. `business_management` no hizo falta para esta cuenta; agregarlo solo si el rol de la página viene de Business Manager y alguna llamada empieza a devolver 200 de permisos.

### Medios

8. **ManyChat sigue en el código y el token está vacío.** Hay `POST /api/webhooks/manychat`, el campo `reel.keyword` y `keyword_match.py`. `MANYCHAT_WEBHOOK_TOKEN` está vacío, así que el webhook respondería 503. Neon no quedó: no hay `DATABASE_URL` ni referencias a Neon en `backend/src`.
   - Solución: si ManyChat sigue en alcance, generar `MANYCHAT_WEBHOOK_TOKEN`. Si se sacó del alcance, borrar webhook, keyword y el mapeo.

9. **Backup y cron no están activos.** `scripts/backup.sh` existe y hace `docker exec audiencia-db pg_dump`. No hay crontab en esta máquina, no existe `/opt/atv-audiencia/backups/` y no hay ningún `.sql.gz`.
   - Solución: en el VPS, `chmod +x scripts/backup.sh` y `0 4 * * * /opt/atv-audiencia/scripts/backup.sh >> /var/log/atv-audiencia-backup.log 2>&1`.

10. **Claude CLI no está instalado en el host.** El Dockerfile lo instala con `npm install -g @anthropic-ai/claude-code` al construir la imagen. Esa imagen no se construyó. `ANTHROPIC_API_KEY` está vacía.
    - Solución: build del backend en el VPS y cargar la API key, o dejar una sesión del CLI dentro del contenedor.

11. **El porcentaje no se pudo contrastar con un reel guardado.** La fórmula del código es `round(calificados * 100 / total_interacciones, 1)` y 0 si el total es 0. No hay filas.
    - Solución: después de la primera corrida, tomar un reel y comparar `calificados`, `total_interacciones` y `pct_calificado` contra un `COUNT` SQL.

### Bajos

12. **`GET /api/health` no pide sesión.** El resto de la API de reels y rúbrica sí usa la cookie `ecosystem_session`. El webhook usa `X-Webhook-Token`, no la cookie.
    - Solución: dejar `/api/health` abierto para el healthcheck. No publicar otro endpoint sin `require_session`.

13. **`.env.example` tiene valores no secretos** (`POSTGRES_DB=audiencia`, `POSTGRES_USER=audiencia`, puertos, `IG_GRAPH_VERSION`). Las claves van vacías. El `.env` local sí tiene token, clave de Postgres y secreto de sesión, y está listado en `.gitignore`. Sin git, ese ignore todavía no protege un commit.
    - Solución: inicializar git antes de cualquier commit y no agregar `.env`.

## 4. Detalle por sección

### Estructura

```text
docker-compose.yml
.env.example
nginx/audiencia.atvos.io.conf
scripts/backup.sh
backend/          FastAPI, Pony, APScheduler, Dockerfile con Claude CLI
  src/controllers reels, rubrica, webhook, health
  src/services    pipeline, instagram, graph, classification
frontend/         React 18, Vite 5, .jsx, CSS Modules
```

No hay `.ts`, `.tsx` ni Tailwind en `frontend/src` ni en `package.json`. `node_modules` arrastra tipos de Babel/Vite; eso no es el stack de la app.

ManyChat sigue (webhook, `keyword`, origen `manychat`). Neon no.

### Seguridad

Búsqueda de `EAA` en `backend/src` y `frontend/src`: sin coincidencias. El token vive solo en `.env`. No hay historial de git donde pueda estar commiteado.

Postgres en el compose no publica `5432`. Solo el backend lo alcanza por `DB_HOST=audiencia-db`.

Auth:

| Ruta | Auth |
| --- | --- |
| `GET /api/health` | No |
| `GET /api/reels` | Cookie `ecosystem_session` |
| `GET /api/reels/{id}/calificados` | Cookie |
| `GET/PUT /api/rubrica` | Cookie |
| `POST /api/webhooks/manychat` | Header de token, no cookie |

### Base de datos

Compose: imagen `postgres:18`, volumen nombrado `audiencia-pgdata` en `/var/lib/postgresql`, healthcheck `pg_isready`, backend con `depends_on: condition: service_healthy`. Contenedores previstos: `audiencia-db`, `audiencia-backend`, `audiencia-frontend`.

Conteos: no disponibles. El servicio no está arriba.

`scripts/backup.sh` sí existe. Cron: no. Backups generados: no.

### Instagram

`debug_token` (HTTP 200), sin pegar el token:

| Campo | Valor |
| --- | --- |
| is_valid | true |
| type | USER |
| expires_at | 0 (Graph lo trata como token sin vencimiento) |
| data_access_expires_at | 2026-12-02T14:27:23Z |
| scopes | `pages_show_list`, `instagram_basic`, `instagram_manage_insights`, `instagram_manage_messages`, `pages_read_engagement`, `public_profile` |

`GET /me/permissions` repite esos seis permisos en `granted`.

`instagram_manage_comments` y `business_management`: ausentes de la lista. La llamada real de comentarios, sobre el reel `18194353774376052` (21 de septiembre de 2026, `REELS`), devolvió HTTP 200 y 1 comentario con `limit=1`.

Los últimos cinco medios de la cuenta incluyen cuatro reels y un carrusel. El más reciente es un reel del 21 de septiembre de 2026.

No hay job de renovación ni tabla `ig_token`.

`scripts/test_ig.py`: no existe. Output resumido del chequeo manual:

```text
DEBUG 200 is_valid=true expires_at=0 data_access_expires_at=2026-12-02 type=USER
scopes=pages_show_list, instagram_basic, instagram_manage_insights,
       instagram_manage_messages, pages_read_engagement, public_profile
MEDIA 200  n=5  (4 REELS + 1 FEED)
COMMENTS 200  n=1  en el reel más reciente, limit=1
BD is_verified  400  (#100) Tried accessing nonexisting field (is_verified)
BD sin ese campo  200  ver sección siguiente
```

### Pipeline

Un solo job de APScheduler: `audiencia-pipeline`, `IntervalTrigger(minutes=30)`, `max_instances=1`, más una corrida al arrancar el proceso. No hay logs: el proceso no arrancó.

Rate limit: códigos 4, 17, 32, 613 y también 80002, más HTTP 429. Backoff 2 s, se duplica hasta 60 s, 4 intentos, en `graph_client.request_json`. Las fases del pipeline cortan al agotar el backoff.

HTTP sync y el subprocess de Claude van en `asyncio.to_thread` (`fetch_reel_page`, comentarios, `discover_profile`, `classify_profile` y los upserts).

Business Discovery en la base: 0 enriquecidos, 0 fallidos. No hubo corrida.

Ejemplo real, cuenta `instagram`, sin `is_verified` (HTTP 200). Las claves devueltas fueron solo `biography`, `followers_count`, `id`, `website`:

```json
{
  "id": "17841400039600391",
  "website": "http://help.instagram.com",
  "followers_count": 686584231,
  "biography": "Discover what's new on Instagram",
  "is_verified": "campo ausente"
}
```

Con `is_verified` en el field expansion, HTTP 400:

```json
{"code": 100, "message": "(#100) Tried accessing nonexisting field (is_verified)", "type": "OAuthException"}
```

El tilde no viene.

### Clasificación

Comando exacto:

```text
claude -p "<prompt>" --output-format json --dangerously-skip-permissions
```

Timeout 120 s. Si hay `ANTHROPIC_API_KEY`, se pasa al entorno del subprocess. El JSON se valida (`calificado` bool, `avatar` en la lista, `score` 0–100, `motivo` no vacío). Si es inválido, reintenta una vez. Si falla de nuevo, se loguea y el perfil queda sin fila de clasificación para la próxima corrida.

No se reclasifica si `clasificado_at` tiene menos de 30 días. Cuentas marcadas `personal_o_inaccesible` no pasan por Claude: se guardan como `sin_datos` / `calificado=false`.

Claude no está instalado en este host y el contenedor no existe.

Clasificaciones reales: no hay. No se pueden mostrar 10 filas.

Distribución: 0 calificados, 0 no calificados, 0 sin datos.

### API

| Método | Ruta | Devuelve |
| --- | --- | --- |
| GET | `/api/health` | `{ok, service}` |
| GET | `/api/reels` | Reels con `total_interacciones`, `calificados`, `pct_calificado`, fecha descendente |
| GET | `/api/reels/{id}/calificados` | Página de calificados. Default `limit=50`. El preview usa `limit=5` |
| GET | `/api/rubrica` | Texto de la rúbrica |
| PUT | `/api/rubrica` | Actualiza el texto |
| POST | `/api/webhooks/manychat` | Crea la interacción idempotente |

`pct_calificado` contra un reel real de la base: no verificable. No hay filas.

### Frontend

Vista principal: dos columnas, “Reels” y “Personas calificadas”, preview de 5. El botón del porcentaje llama `onOpenAll` y abre `?vista=todos`. Vista “Ver todos”: “Volver”, título, “N leads calificados”, porcentaje y grilla paginada de a 50.

Estilo: variables de ATV-MKT en `frontend/src/index.css`. Fondo `#050505`, cards `#0C0C0E`, acento `#E63946`, fuente Inter. A 390 px las columnas se apilan (`@media (max-width: 860px)`). Esa prueba de layout se hizo antes, con una API de humo. Esta auditoría no volvió a abrir el browser y no hay API real sirviendo datos.

### Deploy

Contenedores: inexistentes. Nginx: solo el archivo del repo, `server_name audiencia.atvos.io`, `listen 80`, sin SSL. `/api/` y `/api/webhooks/` hacen `proxy_pass http://127.0.0.1:8020` sin path, así que el prefijo llega al backend. El frontend va a `127.0.0.1:3020`.

Código del VPS contra el último commit: no aplicable. No hay commit ni acceso al VPS desde esta auditoría.
