# May Roundtable Schedule

A ready-to-deploy scheduling app for attorneys and lenders.

## What it includes

- Public booking page at `/`
- One-slot-per-registration booking flow
- Automatic slot locking to prevent double booking
- SQLite database storage
- Organizer email notification support
- Organizer SMS notification support through Twilio
- Optional confirmation email to the person who booked
- Admin panel at `/admin.html`
- Admin slot management without editing code

## Local run

```bash
python3 app.py
```

Open:

- Public booking page: `http://127.0.0.1:8000`
- Admin page: `http://127.0.0.1:8000/admin.html`

Default admin PIN:

```text
changeme
```

Set a real PIN before deployment.

## Environment variables

### Required for production

```bash
export ADMIN_PIN="your-secure-pin"
```

### Optional SMTP email notifications

```bash
export SMTP_HOST="smtp.your-provider.com"
export SMTP_PORT="587"
export SMTP_USERNAME="smtp-user"
export SMTP_PASSWORD="smtp-password"
export SMTP_USE_TLS="true"
export FROM_EMAIL="scheduler@yourdomain.com"
export ORGANIZER_EMAIL="organizer@yourdomain.com"
```

### Optional confirmation email to the user

```bash
export SEND_USER_CONFIRMATION="true"
```

### Optional Twilio SMS notifications

```bash
export TWILIO_ACCOUNT_SID="AC..."
export TWILIO_AUTH_TOKEN="..."
export TWILIO_FROM_NUMBER="+15555555555"
export TWILIO_TO_NUMBER="+15555555555"
```

## How booking works

1. The public page loads all slots from SQLite.
2. A user selects one available slot.
3. The form collects:
   - Full Name
   - Email Address
   - Optional Company / Role
   - Attending role
   - Optional notes
4. On submit, the backend:
   - verifies the slot is still available
   - creates the registration
   - marks the slot as booked
   - sends organizer email if SMTP is configured
   - sends organizer SMS if Twilio is configured
   - optionally sends a confirmation email to the user

## Admin workflow

1. Open `/admin.html`
2. Enter the admin PIN
3. Add, edit, or delete slots
4. Review registrations in the table

## Render deployment

This app is ready for Render.

### Files already included

- `render.yaml`
- `requirements.txt`
- `.gitignore`

### Important production note

Bookings are stored in SQLite, so Render should use a persistent disk.
The included `render.yaml` already mounts a disk at `/var/data` and points the app there through `DATA_DIR=/var/data`.

### Deploy steps

1. Push this project to GitHub.
2. In Render, choose:
   - `New` -> `Blueprint`
   - select your repository
3. Render will read `render.yaml` automatically.
4. Set these secret environment variables in Render:
   - `ADMIN_PIN`
   - `ORGANIZER_EMAIL`
   - optional SMTP values
   - optional Twilio values
5. Deploy.

After deploy, Render will give you a public URL such as:

```text
https://may-roundtable-schedule.onrender.com
```

### Admin access after deploy

- Public booking page: `/`
- Admin page: `/admin.html`

## Deployment notes

This app uses only Python standard library modules, so it can deploy anywhere you can run Python 3.9+.

### Simple VPS or server

Run:

```bash
python3 app.py
```

For production, place it behind Nginx or Caddy and run it with a process manager such as:

- `systemd`
- `supervisord`
- `pm2` running the Python command

### Example reverse proxy flow

1. Point your domain to the server
2. Run the app on port `8000`
3. Proxy traffic from Nginx/Caddy to `127.0.0.1:8000`
4. Set environment variables for admin, email, and SMS

## Database

The app creates `scheduler.db` automatically in the configured data directory.

Local default:

```text
./scheduler.db
```

Render default from `render.yaml`:

```text
/var/data/scheduler.db
```

If you want PostgreSQL later, the fastest upgrade path is swapping the SQLite queries in `app.py` for a Postgres driver while keeping the same HTTP API and front end.
