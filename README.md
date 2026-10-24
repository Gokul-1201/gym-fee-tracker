# Gym tracker — Fee Tracker (Django)

Member registration, monthly/annual fee tracking, payment history, due-date reminders, attendance,
reports, WhatsApp/SMS reminders, QR check-in and a mobile-app REST API.

## 1. Quick start

```bash
python -m venv venv
venv\Scripts\activate            # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt

python manage.py makemigrations gym
python manage.py migrate
python manage.py createsuperuser # optional: or use the Create account page in the browser
python manage.py seed_demo       # optional: sample members, payments, attendance
python manage.py runserver
```

Open http://127.0.0.1:8000/ (if Windows blocks the port: `python manage.py runserver 8080`).
Sign in, or click **Create account** (`/register/`). The first account created there becomes the owner (superuser);
later accounts need the signup code `STAFF_SIGNUP_CODE` from settings.py — **change it**. `/admin/` is the Django admin.

## 2. How the fee tracking works

1. **Plans** → create monthly / annual plans with a price.
2. **Register member** → pick a plan. A member ID (GR0001…) and a private QR token are generated.
   The first fee is due on the joining date.
3. **Record payment** → choose member, how many months/years it covers, method. The member's
   `next_due_date` moves forward (early renewals extend from the current due date; late ones start today).
   A printable receipt is created.
4. **Dues** page lists *overdue* and *due soon* members. Dashboard shows revenue, pending amount, visits.

## 3. Automated WhatsApp / SMS reminders

Reminders go to every active member whose fee is due within `REMINDER_DAYS_BEFORE` days (default 3) or overdue,
at most once per `REMINDER_COOLDOWN_DAYS` (default 2). Every attempt is stored in **Reminders**.

By default `NOTIFY_CHANNELS=console`, which only prints messages in the terminal. For real sending
create a Twilio account and set environment variables:

```bash
set NOTIFY_CHANNELS=whatsapp,sms
set TWILIO_ACCOUNT_SID=ACxxxxxxxx
set TWILIO_AUTH_TOKEN=xxxxxxxx
set TWILIO_SMS_FROM=+1XXXXXXXXXX
set TWILIO_WHATSAPP_FROM=whatsapp:+14155238886     # Twilio sandbox or approved sender
set DEFAULT_COUNTRY_CODE=+91
```

(Use `export` instead of `set` on Mac/Linux.) Ways to run them automatically:

* **Built-in scheduler:** `set RUN_SCHEDULER=1` then start the server — sends daily at `REMINDER_HOUR` (default 9 AM).
* **Cron / Task Scheduler:** `python manage.py send_reminders` once a day.
* **Manual:** the *Send reminders now* button on Dues / Reminders pages.

Note: WhatsApp business-initiated messages need an approved template with Twilio in production.

## 4. QR check-in

* Each member has a QR on their profile page (and a printable ID card).
* **QR check-in** page opens the camera (needs HTTPS or localhost), or accepts a USB scanner.
  Scanning twice on the same day does not create a duplicate. Overdue members are allowed in with a warning
  (`ALLOW_OVERDUE_CHECKIN` in settings).

## 5. Mobile app API

Create a member's app login on their profile (**Create app login** — password is shown once).

```bash
# get a token
curl -X POST http://127.0.0.1:8000/api/auth/token/ -d "username=gr0001&password=XXXX"
# then
curl -H "Authorization: Token <token>" http://127.0.0.1:8000/api/me/            # profile + fee status
curl -H "Authorization: Token <token>" http://127.0.0.1:8000/api/me/payments/
curl -H "Authorization: Token <token>" http://127.0.0.1:8000/api/me/attendance/
curl -H "Authorization: Token <token>" http://127.0.0.1:8000/api/me/qr/ -o my_qr.png
```

Staff-only endpoints (use a staff user's token): `POST /api/checkin/` with `{"token": "<qr text>"}`,
`GET /api/members/?q=&state=overdue`, `GET /api/summary/`. Any mobile stack (Flutter, React Native, Kotlin, Swift)
can use these endpoints.

## 6. Going live

Set `DJANGO_DEBUG=0`, a strong `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=yourdomain.com`, run
`python manage.py collectstatic`, serve with gunicorn + nginx (or WhiteNoise), use HTTPS, and switch to PostgreSQL if needed.
Change the brand text with `GYM_NAME` (default `Gym tracker`).

## Project layout

```
manage.py
gym_project/      settings, urls
gym/              models, views, forms, api_views, services/ (notifications, reminders, checkin, qr)
  management/commands/   send_reminders, seed_demo
templates/gym/    all pages     static/css/style.css   static/js/app.js
```
