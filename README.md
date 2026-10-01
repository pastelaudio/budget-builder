# Budget Builder

Generates a universal monthly budget template as an Excel workbook or a
Google Sheet. All totals (income, expenses, remaining balance, savings rate)
are live formulas, so they recalculate automatically whenever you type new
income or expense values — no code needs to run again.

## Layout

- **Income**: one row per source, `Total Income = SUM(...)`
- **Expenses**: Category / Budgeted / Actual / Difference (`=Budgeted-Actual`),
  overspent categories (Difference < 0) are highlighted in red
- **Summary**: Total Income, Total Expenses, Remaining Balance, Savings Rate

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run the GUI

```powershell
python gui.py
```

Edit the income/expense rows (add or remove as needed), then click
**Export to Excel (.xlsx)** or **Export to Google Sheets**.

## Headless / CLI use

```powershell
python cli.py --month "November 2026" --out budget_nov.xlsx
python cli.py --month "November 2026" --out budget_nov.xlsx --sheets
```

## Google Sheets setup (one-time)

Google Sheets export needs an OAuth client so the app can create a sheet on
your behalf:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/), create
   (or pick) a project, and enable the **Google Sheets API**.
2. Under **APIs & Services > Credentials**, create an **OAuth client ID** of
   type "Desktop app".
3. Download the JSON and save it as `credentials.json` in this project's root
   folder (next to `gui.py`).
4. The first time you export to Google Sheets, a browser window opens asking
   you to sign in and grant access. A `token.json` is cached afterward so you
   won't need to sign in again.

`credentials.json` and `token.json` are git-ignored — never commit them.

## Build a standalone .exe

```powershell
pip install pyinstaller
python build_exe.py
```

This produces `dist/BudgetBuilder.exe`, a double-clickable app that doesn't
require Python to be installed. If you plan to use Google Sheets export from
the `.exe`, copy `credentials.json` next to the `.exe` file.

## Use it on iPad / any browser (web app)

`webapp.py` serves the same budget tool (dynamic rows, live totals, pie chart,
Excel/Sheets export) as a web page, so it works on iPad Safari, Android, etc.

**Option A — quick local use on your home Wi-Fi:**

```powershell
python webapp.py
```

Note the LAN URL it prints (e.g. `http://192.168.1.23:5000`) and open that on
the iPad's browser, same Wi-Fi network required. No install on the iPad.

**Option B — split deployment (frontend on Netlify, backend elsewhere):**

Netlify Functions only support JavaScript/TypeScript/Go, not Python, so this
project deploys as two pieces:

1. **Backend (Flask API)** — deploy `webapp.py` to a Python host such as
   [Render](https://render.com), Railway, or Azure App Service:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn webapp:app` (see `Procfile`)
   - Set the `PORT` env var if your host requires it (most set it automatically)
   - If you want Google Sheets export to work there, upload `credentials.json`
     as a secret file and complete the OAuth flow once (the host needs a way to
     open a browser, or pre-generate `token.json` locally and upload it too)
2. **Frontend (static site)** — deploy the `web/` folder to Netlify
   (`netlify.toml` already points `publish` at `web/`):
   - Edit `API_BASE_URL` at the top of `web/app.js` to your backend's public
     URL (e.g. `https://your-app.onrender.com`), since the frontend and
     backend are on different domains
   - Push to a Git repo and connect it in Netlify, or drag-and-drop the `web/`
     folder in the Netlify dashboard

CORS is already enabled on the Flask side (`flask-cors`) for the `/export/*`
routes so the Netlify-hosted frontend can call the separately hosted backend.
