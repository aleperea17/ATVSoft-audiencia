# Pre-deploy — ATV Audiencia

## Archivos modificados

- `.env.example` — salió `MANYCHAT_WEBHOOK_TOKEN`. Entraron `PIPELINE_MAX_REELS=5`, `PIPELINE_MAX_PERFILES=50` y `DISCORD_WEBHOOK_URL`.
- `.gitignore` — cubre `.env`, `node_modules`, `dist`, `__pycache__` y `backups/`.
- `backend/main.py` — sin el router de ManyChat. Job diario del token a las 9:00, `America/Argentina/Buenos_Aires`.
- `backend/src/classification_json.py` — eliminada `apply_rubric_gate`.
- `backend/src/db.py` — rúbrica nueva. Ya no se agrega la columna `keyword`.
- `backend/src/models.py` — sin `reel.keyword`.
- `backend/src/schemas.py` — sin `keyword` ni los modelos de ManyChat.
- `backend/src/services/classification_service.py` — el modelo recibe `followers_count` y su `calificado` se guarda tal cual.
- `backend/src/services/instagram_service.py` — Business Discovery pide `biography,website,followers_count,media.limit(8){caption}`. `verificado` queda `null`.
- `backend/src/services/pipeline_services.py` — topes opcionales. Sin las variables, no hay corte por cantidad.
- `backend/src/services/reels_services.py` — la respuesta de reels no incluye `keyword`.
- `backend/tests/test_logic.py` — sin keyword ni compuerta. Nginx ya no espera `/api/webhooks/`.
- `nginx/audiencia.atvos.io.conf` — solo `/api/` hacia `127.0.0.1:8020`, sin path en el `proxy_pass`.

## Archivos nuevos

- `backend/scripts/test_ig.py`
- `backend/src/pipeline_runner.py` — `python -m src.pipeline_runner run-once`
- `backend/src/services/token_watch_service.py`
- `DEPLOY.md`

## Archivos eliminados

- `backend/src/keyword_match.py`
- `backend/src/controllers/webhook_controller.py`
- `backend/src/services/webhook_services.py`

## `git ls-files | grep -i env`

```text
.env.example
backend/src/setup_env.py
```

`.env` no está en el índice. `setup_env.py` aparece porque el nombre contiene `env`: es el cargador de variables, no un archivo de secretos.

## Repo

`gh` no está instalado en esta máquina, así que el repo privado no se creó desde acá.

El remoto `origin` sigue siendo el público anterior:

https://github.com/aleperea17/ATVSoft-audiencia

Ese remoto no recibió este commit. El deploy tiene que clonar el privado, cuando exista:

https://github.com/aleperea17/atv-audiencia

Crearlo sin pisar `origin`:

```bash
gh repo create atv-audiencia --private --source=. --remote=private --push
```

## Pendiente para Franco

1. Crear el repo privado `atv-audiencia` con el comando de arriba y pushear `master`. Después clonar ese URL en el VPS, no el de `ATVSoft-audiencia`.
2. Copiar `ECOSYSTEM_SESSION_SECRET` de los otros módulos. Este proceso solo verifica la cookie. El login tiene que emitirla con `Domain=.atvos.io`. Si el dominio o el secreto difieren, `audiencia.atvos.io` responde 401 en la API.
3. Pegar `IG_ACCESS_TOKEN` en el `.env` del VPS. No está en git.
4. Completar `ANTHROPIC_API_KEY`. Vacía, el contenedor no clasifica.
5. `DISCORD_WEBHOOK_URL` es opcional. Sin ella, el aviso de vencimiento solo se loguea.
6. El token de Graph es válido. `expires_at` es 0. `data_access_expires_at` es 2026-12-02 14:27 UTC. El job avisa si falta menos de 10 días.
7. Falta el scope `instagram_manage_comments`. En una lectura real, 50 comentarios del reel más nuevo trajeron `id`, `text` y `timestamp`, y ninguno trajo `username`. `scripts/test_ig.py` llega hasta los 3 comentarios y no puede hacer Business Discovery del primer comentarista. El pipeline tampoco puede armar interacciones hasta que Graph devuelva el username.
8. La rúbrica nueva se inserta solo si la tabla `rubrica` está vacía. Un Postgres nuevo del VPS la recibe. Una base ya sembrada conservaría el texto viejo.
9. `PIPELINE_MAX_PERFILES` toca por separado el enriquecimiento y la clasificación: cada fase toma como máximo N perfiles y el resto queda para la corrida siguiente.
10. `REPORTE_ATV_AUDIENCIA.md` y `AUDITORIA_ATV_AUDIENCIA.md` describen ManyChat y la compuerta del tilde. Quedaron así a propósito.
11. En esta máquina no hay Docker. Pytest: 6 passed. `python -m src.pipeline_runner` sin argumentos sale con código 2 y el texto de uso. `scripts/test_ig.py` corrió en local, sin escribir en la base.
