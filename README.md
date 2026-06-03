# FR24 GPT Backend Starter

This starter backend implements:

Custom GPT -> Secure Backend API -> FR24 API -> Excel file generator -> downloadable .xlsx

It does not use Google Sheets.

## Files

- `app/main.py` - FastAPI endpoints
- `app/fr24_client.py` - FR24 API client and 14-day chunking
- `app/report_builder.py` - Excel report builder
- `app/mapping.py` - MSN-to-registration mapping
- `app/security.py` - backend API key and signed download links
- `data/aircraft_map.csv` - your MSN mapping table
- `openapi_gpt_action.yaml` - paste this into GPT Actions after replacing the server URL
- `.env.example` - environment variables to configure

## Local test

```bash
cp .env.example .env
# edit .env with real values
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

Create a report by registration:

```bash
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $BACKEND_API_KEY" \
  -d '{"registration":"EI-EIN","days":20}'
```

Create a report by MSN:

```bash
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $BACKEND_API_KEY" \
  -d '{"msn":"39764","days":20}'
```

## GPT Action setup

1. Deploy the backend to Render, Railway, Fly.io, AWS, Azure, or another HTTPS host.
2. Replace the server URL in `openapi_gpt_action.yaml` with your real backend URL.
3. In Custom GPT builder, create an Action.
4. Use API Key authentication.
5. Header name: `X-API-Key`.
6. Paste your `BACKEND_API_KEY` into the GPT Action auth field.
7. Paste the OpenAPI schema.

The FR24 API token stays only in your backend environment variables.
