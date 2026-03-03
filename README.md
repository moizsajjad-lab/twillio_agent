# Twilio Voice Agent + Google Calendar CRUD

This service answers Twilio Voice calls, streams audio to OpenAI Realtime, and can **create / list / update / delete** Google Calendar events via tool-calling.

## Setup

### 1) Python deps

```bash
python -m pip install -r requirements.txt
```

### 2) Environment variables

Copy `.env.example` to `.env` and fill values.

Required:
- `OPENAI_API_KEY`
- `DEFAULT_TIMEZONE` (recommended; default is `Asia/Karachi`)
- `GOOGLE_CALENDAR_ID`
- Either `GOOGLE_SERVICE_ACCOUNT_FILE` **or** `GOOGLE_SERVICE_ACCOUNT_JSON`

Quick test (verifies Calendar access using your `.env`):

```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import google_calendar; print(google_calendar.list_events(max_results=3))"
```

### 3) Google Calendar service account

This project uses a **Google Cloud service account** (server-to-server).

High-level steps:
- Create a Google Cloud project
- Enable **Google Calendar API**
- Create a **Service Account** and generate a JSON key file (download it)
- In Google Calendar UI, share the calendar you want to manage with the service account email (looks like `...@...iam.gserviceaccount.com`)
  - Grant permission: **Make changes to events**
- Set `GOOGLE_CALENDAR_ID` to that calendar’s Calendar ID (Calendar settings → *Integrate calendar* → *Calendar ID*)

### 4) Twilio webhook

Point your Twilio Voice webhook to:
- `POST https://<your-host>/incoming-call`

Your host must be publicly reachable with **wss** support (e.g., a proper domain, or an HTTPS tunnel that supports WebSockets).

## Run

```bash
python main.py
```

Server listens on port `8000`.

## Run on Replit (instead of ngrok)

1) Create a new Python repl and upload this project (or import from GitHub).

2) In Replit, add these Secrets (Tools → Secrets):
- `OPENAI_API_KEY`
- `DEFAULT_TIMEZONE` = `Asia/Karachi`
- `GOOGLE_CALENDAR_ID`
- **Either**
  - `GOOGLE_SERVICE_ACCOUNT_JSON` (paste the full service account JSON as a single value)
  - **or** upload the JSON file and set `GOOGLE_SERVICE_ACCOUNT_FILE` to its path

3) Click **Run**. Replit sets `PORT` automatically; this project reads it.

4) Copy your Replit public URL and set your Twilio Voice webhook to:

`https://<your-replit-domain>/incoming-call` (POST)

