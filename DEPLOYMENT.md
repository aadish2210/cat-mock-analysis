# Deploy to Vercel and Supabase

This repository deploys as a Vite static frontend plus a Flask serverless function. Supabase provides authentication and user-scoped persistence.

## Security model

- The browser signs users in with the official Supabase client.
- Every protected Flask request includes the user's short-lived access token.
- Flask verifies that token with Supabase Auth.
- Flask accesses PostgREST using the same user token, never a service-role key.
- PostgreSQL row-level security enforces `auth.uid() = user_id`.
- IMS report URLs and JWTs are used only while an import runs and are never stored.

## 1. Create the Supabase project

1. Open `https://supabase.com/dashboard` and sign in.
2. Click **New project**.
3. Select or create an organization.
4. Name the project, for example `cat-strategic-diagnostic`.
5. Generate a strong database password and keep it in a password manager. The app does not use it.
6. Choose the region nearest the users.
7. Click **Create new project** and wait for provisioning.

## 2. Install the database schema

1. In Supabase, open **SQL Editor**.
2. Click **New query**.
3. Open `supabase/migrations/20260904000000_initial.sql` from this repository.
4. Copy the entire file into the SQL Editor.
5. Click **Run** and confirm it completes without errors.

The migration is idempotent. It creates profiles, mock attempts, question reviews, indexes, triggers, foreign keys, a health RPC, and row-level security policies.

## 3. Copy the public API values

1. Open **Project Settings** in Supabase.
2. Open **API** or **API Keys**.
3. Copy the **Project URL**, such as `https://abcdefgh.supabase.co`.
4. Copy the **Publishable key**, normally beginning with `sb_publishable_`.
5. A legacy `anon` / `public` key also works.

Never use a key beginning with `sb_secret_` or a legacy `service_role` JWT. The application rejects privileged keys.

## 4. Configure Supabase Auth

1. Open **Authentication > Providers > Email**.
2. Ensure Email is enabled.
3. Keep email confirmation enabled for a public application.
4. Open **Authentication > URL Configuration**.
5. You can temporarily keep the default Site URL. Update it after Vercel assigns the production URL.

For multiple real users, configure custom SMTP. Supabase's default email service is intended for testing and has delivery/rate limits.

## 5. Put the source in a private Git repository

Vercel works most reliably from GitHub, GitLab, or Bitbucket.

1. Create a new **private** repository.
2. Upload the contents of `cat-mock-analytics`, not its parent folder.
3. Confirm `.env`, `data/*.json`, `node_modules`, `frontend/dist`, and Python caches are absent.
4. Commit and push.

The supplied ZIP is already source-only and secret-scanned.

## 6. Import the project into Vercel

1. Open `https://vercel.com/new`.
2. Import the private Git repository.
3. Keep the repository root as **Root Directory**.
4. Select **Other** if Vercel asks for a framework preset.
5. Do not override build settings. `vercel.json` defines:
   - install: `npm --prefix frontend ci`
   - build: `npm --prefix frontend run build`
   - output: `frontend/dist`
   - API rewrite to `api/index.py`
   - SPA fallback to `index.html`
6. Add these environment variables:

```text
SUPABASE_URL = https://YOUR_PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY = YOUR_PUBLIC_PUBLISHABLE_KEY
```

Add both to Production, Preview, and Development if previews should work. Do not prefix them with `VITE_`; Flask provides public runtime configuration via `/api/config`.

7. Click **Deploy** and wait for both builds.

## 7. Connect Vercel to Supabase Auth

Suppose Vercel assigns `https://cat-strategic-diagnostic.vercel.app`.

1. Return to **Supabase > Authentication > URL Configuration**.
2. Set **Site URL** to the exact production URL.
3. Add the same URL under **Redirect URLs**.
4. Add preview URLs only if preview authentication is required.
5. Save and reload the deployed app.

Magic links use the current browser origin, so that exact origin must be allowed.

## 8. First-run and isolation verification

1. Open the Vercel URL and confirm the sign-in screen appears.
2. Create Account A and confirm its email if required.
3. Sign in and import one fresh IMS View Solutions URL.
4. Confirm the coach cockpit and question bank populate.
5. Open a question and mark it **Learning** with a note.
6. Sign out and create Account B with a different email.
7. Confirm Account B starts with zero mocks and reviews.
8. Sign back into Account A and confirm its data remains.

This verifies application scoping and database RLS.

## 9. Optional local preflight

Create `.env` from `.env.example`, set the two public values, then run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check_supabase.py
```

Expected output has three `[PASS]` lines for environment, Auth, and schema.

Build and test:

```powershell
Set-Location frontend
npm ci
npm run build
npm run lint
Set-Location ..
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe server.py
```

For local magic links, add these Supabase redirect URLs:

```text
http://127.0.0.1:5000
http://localhost:5000
```

## 10. Updating

1. Pull or copy updated source.
2. Run new SQL files under `supabase/migrations` in filename order.
3. Run backend tests and frontend build/lint.
4. Commit and push. Vercel redeploys automatically.

## Troubleshooting

- **Vercel says Supabase configuration is missing:** add both environment variables and redeploy.
- **Data calls report schema-cache/table errors:** rerun the SQL migration and wait briefly for PostgREST.
- **Magic link opens the wrong host:** correct Site URL and Redirect URLs.
- **Confirmation email does not arrive:** inspect Auth logs, email settings, rate limits, and custom SMTP.
- **One user can see another user's data:** disable deployment immediately and rerun the RLS migration.
- **IMS import times out:** copy a fresh View Solutions URL and retry. The function limit is 60 seconds.
- **VARC options look encoded:** re-import using the current importer, which decodes IMS base64 option HTML.
- **Preview login fails:** add the exact preview origin to Supabase Redirect URLs or authenticate only on production.
