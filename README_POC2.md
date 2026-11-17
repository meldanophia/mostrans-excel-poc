# POC 02 — Excel Online → Flask (dummy only)

## What changed
- `web/taskpane.html`: new **Test Connection** and **Send Dummy Data** buttons.
- `flask_poc_api.py`: demo `/poc/health` and `/poc/echo` routes, **no database connection**.
- Existing manifest remains valid because task pane URL and requested permissions have not changed.

## A. Update Github Pages
Replace just `web/taskpane.html` in public repo `meldanophia/mostrans-excel-poc` with the file from this ZIP. Commit to main. Wait for Pages deployment to finish and refresh Excel Online. If caching persists, close/reopen workbook, or increment manifest Version and re-upload.

## B. Test local Flask (optional)
```powershell
pip install Flask
python flask_poc_api.py
```
Open http://127.0.0.1:6077/poc/health to confirm the backend runs. **Excel Online needs a reachable HTTPS endpoint**, so this localhost URL is not enough for task-pane fetch.

## C. Deploy Flask staging over HTTPS
Use your own staging server/reverse proxy/domain. Do not attach DB. On staging, the server must respond with `Access-Control-Allow-Origin: https://meldanophia.github.io` and handle OPTIONS preflight. If the Flask existing service uses a different domain or load balancer, map these demo routes to it only after approving staging access.

## D. Test from Excel Online
Open Mostrans Price Tools, enter just your Flask staging HTTPS origin (example https://staging-api.example.com, no suffix). Click **1. Test Connection** then **2. Send Dummy Data**. Expected `received_rows: 3`, `database_used: false`. No workbook rows are sent.

## Important
Never use production endpoints or sensitive spreadsheet data for this POC. GitHub Pages task pane source code is publicly accessible. Stage 3 should implement Microsoft Entra auth and row-level job tracking before real SQL processing.
