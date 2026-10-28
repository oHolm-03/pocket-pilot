# PocketPilot
PocketPilot is a simple personal finance tracker with the goal of assisting young adults in making smarter financial decisions.

## Setup

If you are using an existing Supabase project and the required environment variables are already configured, you can skip the setup steps below and go straight to installing dependencies and running the app.

1. Make sure the required environment variables are available to the app. The app loads `.env` automatically at startup, so this is the usual way to provide them:

   ```powershell
   Copy-Item .env.example .env
   ```

   Then update `.env` with your own values for `SUPABASE_URL`, `SUPABASE_KEY`, and `FLASK_SECRET_KEY`.

   If your environment is already configured elsewhere, you can skip creating `.env` and just make sure those variables are exported in your shell.

2. Run `supabase-user-isolation.sql` in the Supabase SQL Editor. This enables row-level security and removes existing unowned transactions because they cannot safely be assigned to a user.

3. In Supabase Auth settings, enable email/password authentication. In production, enable email confirmation and configure the site URL.

4. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

5. Run the application:

   ```powershell
   python app.py
   ```

The app requires `SUPABASE_URL` and `SUPABASE_KEY` at runtime, plus a `FLASK_SECRET_KEY`. If those are already set in your local environment, you do not need to re-enter them. Keep `.env` private; it is excluded from Git.
