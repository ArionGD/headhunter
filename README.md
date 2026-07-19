# HeadHunt.io — Greenera Farms Lead Finder

A Django prospecting dashboard for Greenera Farms (agroforestry investor
search). Runs live searches against Apollo.io and Snov.io, with an automatic
simulated-data fallback whenever a real API isn't reachable or authorized —
so the UI is always testable, even with zero API credits. No database, no
auth — everything happens in the request/response cycle.

## What's actually built

| Piece | Status | Notes |
|---|---|---|
| Django project (`config/`) | ✅ Done | Django 5.2, `python-dotenv` loads `.env` on boot |
| App (`core/`) | ✅ Done | No `models.py`, no `admin.py`, no migrations — by design |
| Route `/` | ✅ Done | GET renders the empty dashboard, POST runs a search |
| Search form | ✅ Done | Data source picker (Global Apollo / Apollo Contacts / Snov.io / Simulated), keywords, job titles, locations, result count |
| Apollo — Global API | ✅ Done | `POST /api/v1/mixed_people/api_search` — falls back to mock data automatically on 401/403 (plan-restricted) |
| Apollo — Contacts API | ✅ Done | `POST /api/v1/contacts/search` — surfaces the raw error rather than mocking (searches your own saved contacts) |
| Snov.io — Domain Search | ✅ Done | OAuth token fetch → domain-email search → polling for async results; falls back to mock data if `SNOV_CLIENT_ID`/`SNOV_CLIENT_SECRET` are unset |
| Simulated Mode | ✅ Done | Fully offline, randomly generated but realistic-looking prospects — zero external calls, zero credits |
| UI | ✅ Done | Tailwind via CDN, two-column layout, distinct banners for errors vs. plan-restricted vs. simulated data |
| Tests | ⚠️ Smoke-tested only | Confirmed locally: server boots, GET `/` returns 200, and a POST with `search_source=mock` renders 5 prospect cards end-to-end. Live Apollo Global/Contacts and Snov.io calls have **not** been verified with real, working credentials — Apollo returned 403 (plan-restricted) during testing, which is expected/handled behavior. |

## Project layout

```
HeadHunt.io/
├── manage.py
├── requirements.txt
├── .env                        # APOLLO_API_KEY / SNOV_CLIENT_ID / SNOV_CLIENT_SECRET (git-ignored)
├── .gitignore
├── config/                     # project configuration (settings, root URLs, WSGI/ASGI)
│   ├── settings.py             # loads .env, core registered, STATIC_ROOT set for PythonAnywhere
│   ├── urls.py                 # includes core.urls at '/'
│   └── asgi.py / wsgi.py
├── core/                        # the app — dashboard/home page, intentionally model-less
│   ├── views.py                 # dashboard() — routes between global/contacts/snov/mock search sources
│   ├── urls.py
│   └── templates/core/
│       └── dashboard.html       # Tailwind CDN, filter form + results grid + status banners
└── staticfiles/                 # output of `collectstatic` (Django admin's built-in static assets only)
```

## Running it locally

```powershell
cd "d:\ANTI-GRAVITY\HeadHunter\HeadHunt.io"
pip install -r requirements.txt
```

Edit `.env` in the project root and fill in whichever keys you have:

```
APOLLO_API_KEY=your_apollo_key_here
SNOV_CLIENT_ID=your_snov_client_id
SNOV_CLIENT_SECRET=your_snov_client_secret
```

Any key left blank/placeholder just means that data source falls back to
simulated results instead of erroring out.

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/`, pick a data source, and click **Fetch
Prospects**. "Simulated Mode" always works with no keys at all — start there
to see the UI/flow before spending any real credits.

## Deploying to PythonAnywhere (free tier)

### Will it work fully on the free tier? Short answer: no — read this first

PythonAnywhere's **free tier restricts outbound internet access to an
allowlist of domains** (mostly for pip installs and a handful of common
APIs). `api.apollo.io` and `api.snov.io` are **not** on that allowlist as of
this writing. That means on a free PythonAnywhere account:

- ✅ The site loads, the form works, "Simulated Mode" works perfectly (it's
  fully offline — no external HTTP calls at all).
- ❌ Global Apollo API, Apollo Contacts API, and Snov.io searches will fail
  with a connection error (`requests.exceptions.ConnectionError` — ends up
  in the app's red error banner), because PythonAnywhere's free-tier proxy
  blocks the outbound request before it ever reaches Apollo/Snov's servers.

If you need the **real** API calls to work on a hosted deployment (not just
locally), you'd need a PythonAnywhere **paid** plan (their cheapest paid
tier removes the outbound allowlist restriction), or a different host
entirely (Render, Railway, Fly.io, PythonAnywhere-paid, etc. all allow
unrestricted outbound requests even on their lower tiers). That's a hosting
choice, not something fixable in this codebase.

For a free demo of the *dashboard itself* — layout, form, card rendering,
error/fallback states — PythonAnywhere's free tier is genuinely fine, since
Simulated Mode covers that completely.

### Setup steps

1. **Create a free account** at pythonanywhere.com and open a **Bash
   console** from the dashboard.
2. **Upload the project.** Easiest path without git: zip the `HeadHunt.io`
   folder (excluding `.env`, `db.sqlite3`, `__pycache__`) and upload it via
   the **Files** tab, then unzip in the Bash console:
   ```bash
   unzip HeadHunt.io.zip -d ~/HeadHunt.io
   cd ~/HeadHunt.io
   ```
3. **Create a virtualenv and install dependencies:**
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 headhunt-env
   pip install -r requirements.txt
   ```
4. **Recreate `.env`** in `~/HeadHunt.io/.env` with your real keys (use the
   Files tab's built-in editor, or `nano .env` in the Bash console — don't
   paste secrets into any AI chat, including this one).
5. **Run `collectstatic`** (harmless even though there's nothing custom to
   serve beyond Django admin's assets):
   ```bash
   python manage.py collectstatic --noinput
   ```
6. **Go to the Web tab → Add a new web app → Manual configuration →
   Python 3.10.**
7. **Set the virtualenv path** in the Web tab to
   `/home/<your-username>/.virtualenvs/headhunt-env`.
8. **Edit the WSGI configuration file** (linked from the Web tab) to point
   at this project — replace its contents with:
   ```python
   import sys
   import os

   path = '/home/<your-username>/HeadHunt.io'
   if path not in sys.path:
       sys.path.insert(0, path)

   os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
9. **Add a static files mapping** in the Web tab: URL `/static/` →
   Directory `/home/<your-username>/HeadHunt.io/staticfiles`.
10. Click **Reload** on the Web tab. Your app is now live at
    `<your-username>.pythonanywhere.com`.
11. In `config/settings.py`, `ALLOWED_HOSTS = ['*']` already covers
    PythonAnywhere's domain, so no change needed there.

## What is NOT configured yet

- **`DEBUG = True`.** Fine for a personal prototype/demo; if you ever expose
  this beyond yourself, set `DEBUG = False` and list the real host in
  `ALLOWED_HOSTS` instead of `'*'`.
- **Dev `SECRET_KEY`.** Still the auto-generated Django default in
  `settings.py`. Not a real risk for a prototype with no auth/sessions of
  consequence, but don't reuse this key if the project ever grows real user
  accounts.
- **No rate limiting.** Every non-mock click spends real API credits (or
  attempts to, network access permitting). There's no cooldown or
  double-submit guard.
- **`db.sqlite3` is an unused leftover** from Django's default DB
  connection — no app code touches it. Safe to delete or ignore.

## Notes on API behavior worth knowing

- Apollo's Global API commonly returns **403 (plan-restricted)** on free/
  basic Apollo accounts — this isn't a bug, it's Apollo gating programmatic
  search behind paid tiers. The app detects this and shows simulated data
  with a clear amber "API Access Plan Restricted" banner instead of dying.
- Apollo's Contacts API searches **your own saved contacts**, not the open
  Apollo database — it will return nothing useful unless your Apollo account
  already has contacts saved.
- Snov.io's domain search is asynchronous — the view starts a search job and
  polls briefly for results. If Snov is slow to respond, this can add a few
  seconds of latency to that request specifically.
