# Mostrans Phase 2 — /run-service prefix

## Changes
- `app.py`: all endpoints under `/run-service` (including health).
- `web/taskpane.html`: API fetch adds `/run-service` automatically. **Input only HTTPS origin without path**, e.g. `https://api-dev.example.com`.
- `manifest.xml`: points to GitHub Pages for the Office task pane; does not encode backend API endpoint. Preserves original add-in ID, enables `ReadWriteDocument`, bumps version, corrects static assets URLs, and cache-busts task pane URL.
- `worker.py` remains unchanged; it uses PostgreSQL and does not expose HTTP routes.

## Endpoints
- `GET /run-service/health`
- `POST /run-service/api/v1/transporter-prices/preview`
- `POST /run-service/api/v1/transporter-prices/jobs`
- `GET /run-service/api/v1/transporter-prices/jobs/by-request-key`
- `GET /run-service/api/v1/transporter-prices/jobs/<job_id>`
- `GET /run-service/api/v1/transporter-prices/jobs/<job_id>/results`
- `POST /run-service/api/v1/transporter-prices/jobs/<job_id>/sync-ack`

## Nginx (on a shared hostname)
```nginx
location ^~ /run-service/ {
    proxy_pass http://127.0.0.1:6077;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```
**No slash after `6077`**: Nginx forwards `/run-service/...` unchanged. If the existing `/run-service` exact endpoint belongs to another service, the above block routes only `/run-service/` with trailing slash, preserving `location = /run-service`. Make sure other, more specific Nginx rules do not shadow it. **Do not simultaneously strip the prefix in Nginx**.

## Deployment
1. Replace backend `app.py`; `worker.py` does not change. Keep old file as backup.
2. Replace GitHub Pages `web/taskpane.html` with this version. This is necessary: the original JS used `/api/v1/...` with no prefix.
3. Install `manifest.xml` if you want the revised display metadata/cache version; API prefix does NOT require the manifest itself. Same `<Id>` keeps identity stable. Validate asset URLs and icons before installation.
4. Configure `.env`: `ALLOWED_ORIGIN=https://meldanophia.github.io`; `EXECUTE_ALLOWED_HOST` = actual **hostname only**, not path `/run-service`; `ENABLE_PRICE_UPDATE=false` until safe UAT; configure trusted proxy carefully.
5. Test `curl -i https://YOUR-DEV-DOMAIN/run-service/health`, then OPTIONS preflight on `/run-service/api/v1/transporter-prices/preview`.
6. In Excel `Flask HTTPS URL` enter `https://YOUR-DEV-DOMAIN` (without `/run-service`). Validate & Preview first.

**Safety**: Do not remove host/proxy/auth checks for Execute. A public API hostname and a static bearer token do not alone establish trusted authorization for production. Before enabling UPDATE, ensure DEV-only data, verified HTTPS reverse proxy, authenticated access and worker recovery/concurrency controls.
