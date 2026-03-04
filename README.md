# Twilio Voice Agent (FastAPI + OpenAI Realtime + Google Calendar)

Inbound calls hit `POST /incoming-call`, which returns TwiML that starts a Twilio Media Stream to `WSS /media-stream`.
The app bridges audio between Twilio (g711_ulaw) and OpenAI Realtime (g711_ulaw) and supports barge-in (interrupt).

It also exposes Google Calendar CRUD via Realtime function tools:
`create_travel_booking`, `list_travel_bookings`, `find_travel_bookings`, `update_booking`, `delete_booking`.

## Requirements

- Python 3.10+
- A Twilio phone number with Voice enabled
- An OpenAI API key
- (For Calendar tools) A Google **Service Account** with access to a shared Google Calendar

Install deps:

```bash
pip install -r requirements.txt
```

## Environment variables / Secrets

Set these as environment variables locally, or as **Replit Secrets** (recommended for Replit).

- **`OPENAI_API_KEY`**: OpenAI API key (required to run)
- **`GOOGLE_SERVICE_ACCOUNT_JSON`**: service account JSON **string** OR a **file path** to the JSON file
- **`GOOGLE_CALENDAR_ID`**: target calendar ID to operate on (for service accounts, use a specific calendar ID)

### Google Calendar setup (service account)

1. Create a Google Cloud Service Account and download its JSON credentials.
2. In Google Calendar, **share the target calendar** with the service account email and grant **“Make changes to events”** permission.

## Run locally

If port 8000 is free:

```bash
python main.py
```

Or run on a different port:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```

Health check:
- `http://127.0.0.1:8001/`

### Test Twilio inbound calls locally (ngrok)

Twilio must reach your server over the public internet. Use ngrok:

```bash
ngrok http 8001
```

Then set your Twilio Phone Number Voice webhook:
- **A call comes in** → **HTTP POST** to `https://<your-ngrok-domain>/incoming-call`

The app will automatically instruct Twilio to stream audio to:
- `wss://<your-ngrok-domain>/media-stream`

## Deploy/run on Replit

1. Import your GitHub repo into Replit.
2. Add Secrets in Replit:
   - `OPENAI_API_KEY`
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
   - `GOOGLE_CALENDAR_ID`
3. Set the Replit run command to bind to `$PORT`:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

## Twilio configuration (production/Replit)

Set your Twilio Phone Number Voice webhook:
- **A call comes in** → **HTTP POST** to `https://<your-app-domain>/incoming-call`

No other Twilio URLs need to be configured; `/incoming-call` returns TwiML that initiates the Media Stream to `/media-stream`.

## Notes

- Audio formats: g711_ulaw in/out, server VAD enabled.
- Barge-in: when the user starts speaking, the server sends `response.cancel` to stop the model’s current audio.
- Calendar tools run server-side with a service account; do **not** commit `.env` or service account files to GitHub.

