# PocketPilot
PocketPilot is a simple personal finance tracker with the goal of assisting young adults in making smarter financial decisions.  

## Setup

1. Create a local environment file from the example:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Set `SUPABASE_URL`, `SUPABASE_KEY`, and `FLASK_SECRET_KEY` in `.env` using your Supabase project API settings. Use the publishable/anon key, not a service-role key. Generate a random Flask secret with `python -c "import secrets; print(secrets.token_hex(32))"`.
3. Run `supabase-user-isolation.sql` in the Supabase SQL Editor. This enables row-level security and removes existing unowned transactions because they cannot safely be assigned to a user.
4. In Supabase Auth settings, enable email/password authentication. In production, enable email confirmation and configure the site URL.
5. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

6. Run the application:

   ```powershell
   python app.py
   ```

The app loads `.env` at startup. Keep `.env` private; it is excluded from Git.
