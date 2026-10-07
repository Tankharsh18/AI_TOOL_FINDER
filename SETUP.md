# AI Tool Finder - Project Setup

## 1. MySQL
Create the database and `ai_tools` / `users` tables used by the project, then make sure MySQL is running.

## 2. Windows environment variable
Create a **User** environment variable:

- Name: `DB_PASSWORD`
- Value: your MySQL root password

The application reads the password with `os.getenv("DB_PASSWORD")`.

Optional:
- Name: `FLASK_SECRET_KEY`
- Value: a long random secret key

If `FLASK_SECRET_KEY` is not set, the project uses its local student-project fallback key.

## 3. Run
Open a new PowerShell/VS Code terminal after creating the environment variable:

```powershell
python app.py
```

Then open the local Flask address shown in the terminal.

## Notes
- The backend flow and database queries are kept compatible with the existing project.
- Debug mode is disabled.
- Search pagination now handles invalid page values safely.
- The database password is no longer written directly in `app.py`.
