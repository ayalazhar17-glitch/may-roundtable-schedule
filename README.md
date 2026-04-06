# May Roundtable Schedule

A shareable scheduling site for attorneys and lenders, now prepared for `Vercel + Supabase`.

## What it includes

- Public booking page at `/`
- Admin page at `/admin.html`
- One-slot-per-registration flow
- Shared slot locking so everyone sees booked dates update
- Admin login with a private PIN
- Slot management without editing code
- Optional organizer email notifications through Resend
- Optional organizer SMS notifications through Twilio
- Optional confirmation email to the attendee

## Project structure

- `/index.html` public booking page
- `/admin.html` admin dashboard
- `/api/*` Vercel serverless routes
- `/supabase/schema.sql` database tables, booking function, and starter slots
- `/vercel.json` Vercel runtime config
- `/.env.example` required environment variables

## Required accounts

To make this live with a public link, you need:

1. A `Supabase` project
2. A `Vercel` account

Optional:

- `Resend` for email notifications
- `Twilio` for SMS notifications

## Supabase setup

1. Create a new Supabase project.
2. Open the `SQL Editor`.
3. Copy everything from [`supabase/schema.sql`](/Users/ayalazhar/Documents/New%20project/supabase/schema.sql).
4. Run it once.

That creates:

- the `slots` table
- the `registrations` table
- the `book_slot` function that prevents double booking
- your five default May roundtable slots

## Vercel environment variables

Set these in Vercel before deploying:

### Required

- `ADMIN_PIN`
- `ADMIN_SESSION_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

### Strongly recommended

- `ORGANIZER_EMAIL`

### Optional for email

- `FROM_EMAIL`
- `RESEND_API_KEY`
- `SEND_USER_CONFIRMATION`

### Optional for SMS

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER`
- `TWILIO_TO_NUMBER`

Use [`.env.example`](/Users/ayalazhar/Documents/New%20project/.env.example) as your checklist.

## How booking works

1. The public site loads slots from Supabase.
2. A visitor selects one available slot.
3. They submit:
   - full name
   - email
   - optional company / role
   - attendee type
   - optional notes
4. The `/api/book` route calls the `book_slot` database function.
5. That function locks the selected slot and marks it booked.
6. The site refreshes so nobody else can claim the same time.

## Admin workflow

1. Open `/admin.html`
2. Enter the admin PIN
3. Add, edit, or delete slots
4. Review booked attendees

## Deploy to Vercel

1. Push this repo to GitHub.
2. In Vercel, click `Add New...` -> `Project`.
3. Import this GitHub repository.
4. Vercel will detect the app automatically.
5. Add the environment variables listed above.
6. Deploy.

After deploy, Vercel gives you a public link like:

```text
https://may-roundtable-schedule.vercel.app
```

## Important note about your current GitHub repo

If `scheduler.db` is still in GitHub from the earlier upload, delete it from the repo before your final deploy. The new version uses Supabase instead of SQLite.

## Optional notification setup

### Resend

If you want organizer emails:

1. Create a Resend account
2. Verify a sender domain or sender address
3. Set:
   - `RESEND_API_KEY`
   - `FROM_EMAIL`
   - `ORGANIZER_EMAIL`

If `SEND_USER_CONFIRMATION=true`, the attendee also gets a confirmation email.

### Twilio

If you want organizer text alerts:

1. Create a Twilio account
2. Buy or verify a sending number
3. Set:
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_FROM_NUMBER`
   - `TWILIO_TO_NUMBER`

## Notes

- The old Render and SQLite setup has been removed from the app code.
- Slot locking now depends on the Supabase SQL function, not local files.
- Vercel CLI is not required. You can deploy entirely from the Vercel website.
