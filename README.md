# Mostrans POC 05 — Dry Run + Guarded UPDATE STAGING

This package extends working POC 04 (Office Add-in A–K, PostgreSQL master SELECT, Z–AD / AF–AH write-back).

## CRITICAL: default remains read-only

- `POST /poc/price-preview` performs PostgreSQL **SELECT only** and produces a signed preview proof valid for 10 minutes.
- `POST /poc/price-execute` is **DISABLED by default**. It requires `POC_ENVIRONMENT=staging` **and** `ENABLE_PRICE_UPDATE=true`, plus a signed preview proof and typed confirmation `EXECUTE_STAGING`.
- Do not enable Execute against production. Run with a dedicated staging DB, authorized staging credentials, and a workbook copy containing synthetic/non-sensitive rows. **Cloudflare Quick Tunnel is a public transport; the shared POC token is not production authentication.**
- During execution, SQL is written by Flask; no SQL from Excel is accepted.
- At most 50 rows per Execute request, synchronous. A durable per-row log and idempotency key prevent resubmitting the same job/row from applying the same UPDATE twice. This is not yet a production worker queue.

## Business behavior

Based on the original Apps Script UPDATE: `mt_harga_transporter`, filter `transporter_id`, `nomor_sk LIKE %...%`, `asal_id`, `tujuan_id`, `jenis_kendaraan_id`, `tipe_muatan`, `tipe_harga_id`, `start_date`; plus agreed optional `valid_date` VARCHAR, equality including NULL. Only records with `active='A'` are eligible (guard added in POC05). Target **must be exactly one active record**. `0` = NOT_FOUND, `>=2` = AMBIGUOUS, never bulk-update ambiguous matches. `Price` and `TKBM` are still validated in A–K but **not matched in UPDATE**, consistent with uploaded Apps Script; verify intended business rule.

**Important**: `nomor_sk LIKE` is literal substring matching with `%` and `_` escaped. Review if exact equality is preferable. Ensure status column accepts integer `6` and the table uses `inactive_date` timestamp compatible with `NOW()`.

## Setup

1. Copy `web/taskpane.html` to your GitHub Pages repository (`main`), leaving hosting path and existing `manifest.xml` unchanged. Manifest already requires `ReadWriteDocument`.
2. Copy `flask_poc_api.py`, `poc05_extension.py`, `poc05_sql.py` to your *local Flask directory*, keeping your private `.env`, `master_lookup.json` and `DATABASE_URL` locally. These should **never be committed to public GitHub**. `master_lookup.json` must contain your verified master mapping.
3. `py -m pip install -r requirements.txt` (`python-dotenv` now required).
4. Existing environment variables:
   ```dotenv
   DATABASE_URL=postgresql://READONLY_USER:***@STAGING_HOST:5432/STAGING_DB?sslmode=require
   MASTER_LOOKUP_CONFIG=master_lookup.json
   POC_LOOKUP_TOKEN=your-private-random-token-min-24-chars
   POC_PREVIEW_SECRET=your-different-random-secret-min-32-chars
   POC_ENVIRONMENT=staging
   ENABLE_PRICE_UPDATE=false
   # Only later for internal staging (never Quick Tunnel):
   POC_EXECUTE_ALLOWED_HOST=staging-api.example.internal
   ```
   For preview, read-only SELECT permissions are sufficient. Secret values in this example are placeholders.
5. Restart `py flask_poc_api.py` (port 6077) and keep Cloudflare Quick Tunnel running. In Excel Online, click **Baca A–K**, then **Dry Run Harga (SELECT Only)** using the same lookup token from POC04. Review READY / NOT_FOUND / AMBIGUOUS / INVALID.
6. Only if explicitly approving a **staging** UPDATE test: create `poc_price_execution_log` on staging with `prepare_staging.sql`, grant appropriately scoped `INSERT/SELECT/UPDATE` on the log and `SELECT/UPDATE` on `mt_harga_transporter` to your test role (plus sequence rights). Deploy behind company authentication and internal HTTPS with `POC_EXECUTE_ALLOWED_HOST` matching the internal request host, change to `ENABLE_PRICE_UPDATE=true`, and restart Flask. **The public Quick Tunnel cannot execute UPDATE even when this flag is enabled.** Use copied workbook and a single known row first. Execute requires typed `EXECUTE_STAGING`; failed/missing rows are not updated. The update is row-by-row transactional and logged atomically per success. `Write-back Status Execute` writes AF–AH only; it **does not delete successful Excel rows**.
7. After test, set `ENABLE_PRICE_UPDATE=false`, restart Flask, and revoke test UPDATE permissions if no longer needed.

## Safety / retry

- Never blindly retry using a new job key if the first request timed out: inspect `poc_price_execution_log` first. Re-run with same dry-run proof and the same in-memory `job_key` while the page remains open; results are reused.
- Each confirmed row is rechecked against the current DB before UPDATE and updated only by the exact target ID; changed or ambiguous matches return STALE.
- Row failures are logged, but no automatic database rollback of previously successful rows is performed: they are committed per row.
- Excel write-back is NOT atomic with the DB transaction. An Excel failure should not trigger another UPDATE; retain the existing job key/log and reconcile. Production phase requires persistent job identifiers and recovery across browser closes.
- Row IDs like `Sheet1:row-2` are position-based; stable UUIDs and immutable row hashes are needed before production, especially if users can insert/delete rows during jobs.
- `POC_PREVIEW_SECRET` must be stable across Flask restarts during a preview; do not commit it. Never log passwords/tokens.

## Note on environment permissions

A staging user cannot both be strictly SELECT-only and execute UPDATE. Keep preview read-only with dedicated credentials. When enabling staging Execute, use a different, tightly scoped test role. Under no circumstance set an UPDATE-enabled credential on an endpoint exposed via an unauthenticated Cloudflare Quick Tunnel in a real organization; use Entra ID auth and a corporate staging endpoint first.
