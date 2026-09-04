# CAT Strategic Diagnostic

A multi-user CAT preparation portal built with React, Flask, Vercel, and Supabase. It turns IMS mock telemetry into score audits, topper divergence, topic matrices, ranked coaching priorities, simulations, a searchable question bank, and spaced review.

## Production architecture

- **Vercel:** Vite static frontend and Flask serverless API.
- **Supabase Auth:** email/password and magic-link accounts.
- **Supabase Postgres:** per-user mock and review persistence.
- **Row-level security:** users can access only their own rows.
- **IMS imports:** token-bearing report links are used transiently and never stored.

## Deploy

Follow the complete click-by-click guide in [DEPLOYMENT.md](DEPLOYMENT.md).

At a high level:

1. Create a Supabase project.
2. Run [the SQL migration](supabase/migrations/20260904000000_initial.sql) in Supabase SQL Editor.
3. Push this source to a private Git repository.
4. Import that repository into Vercel.
5. Add `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` in Vercel.
6. Set the Vercel production URL in Supabase Auth URL Configuration.
7. Create accounts and import fresh IMS View Solutions links.

Never use a Supabase secret/service-role key. The application rejects privileged keys.

## Local verification

```powershell
Copy-Item .env.example .env
# Edit .env and add the two public Supabase values.

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check_supabase.py

Set-Location frontend
npm ci
npm run build
npm run lint
Set-Location ..

.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe server.py
```

Open `http://127.0.0.1:5000`.

## Transfer package

Create a clean deployment ZIP at any time:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package_transfer.ps1
```

The packager excludes local candidate data, `.env`, Supabase keys, IMS tokens, dependency folders, build output, caches, Git metadata, and old ZIPs. It aborts if JWT-shaped content is detected.

## Project layout

```text
api/index.py                              Vercel Flask entrypoint
frontend/                                 React + Vite application
supabase/migrations/                      PostgreSQL schema and RLS
server.py                                 API, authentication, and routing
importer.py                               Current IMS API normalizer
reporting.py                              Deterministic analytics and coach
supabase_storage.py                       User-scoped PostgREST stores
check_supabase.py                         Credential/schema preflight
setup_supabase.py                         Optional Management API bootstrap
vercel.json                               Vercel build, routes, and headers
```
