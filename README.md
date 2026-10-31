# Data Extraction Bot

A FastAPI service that uses a configurable LangChain chat model to extract explicitly stated resume or invoice details into validated JSON. The service supports Ollama, Google Gemini, and OpenAI.

## Features

- Structured resume and invoice extraction using LangChain `with_structured_output`.
- Pydantic v2 response schemas with field descriptions.
- Switchable LLM provider and model through environment variables.
- Input length limits, retry with exponential backoff, safe provider errors, and basic non-sensitive logging.
- Interactive API documentation at `/docs`.

## Architecture

```text
Client
  -> FastAPI endpoint (input checks)
  -> Extractor (anti-hallucination prompt + up to 3 attempts)
  -> LangChain structured output
  -> Ollama | Gemini | OpenAI
  -> Pydantic validation
  -> JSON response
```

## Folder structure

```text
data-extraction-bot/
|-- app/
|   |-- __init__.py
|   |-- config.py
|   |-- extractor.py
|   |-- llm.py
|   |-- main.py
|   `-- schemas.py
|-- tests/
|   |-- test_api.py
|   `-- test_extractor.py
|-- .env.example
|-- .gitignore
|-- README.md
`-- requirements.txt
```

## Setup on Windows PowerShell

From the project directory:

```powershell
py -3.14 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `LLM_PROVIDER`, `LLM_MODEL`, and any required provider key. `.env` is ignored by Git.

### Provider setup

- **Ollama (default, local):** Install Ollama, pull a model supported by your installed Ollama version, such as `ollama pull <your-model>`, then set `LLM_PROVIDER=ollama` and `LLM_MODEL` to that exact local model name. No API key is required.
- **Gemini:** Create an API key in Google AI Studio. Set `LLM_PROVIDER=gemini`, `LLM_MODEL` to a model available to your account, and `GOOGLE_API_KEY` to your key.
- **OpenAI:** Create an API key in the OpenAI platform and ensure your account has billing configured. Set `LLM_PROVIDER=openai`, `LLM_MODEL` to an available model, and `OPENAI_API_KEY` to your key.

Model names are intentionally supplied through `LLM_MODEL`, not hardcoded by the application. Provider keys are never returned by `/health` or written to application logs.

## Run the application

```powershell
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for Swagger UI. `GET /health` reports the status, provider, and configured model name.

## Example requests

Example resume text:

```text
Jane Doe
Email: jane.doe@example.com
Skills: Python, FastAPI
Education: BSc Computer Science, Example University, 2022
```

PowerShell:

```powershell
$resume = @{ text = "Jane Doe`nEmail: jane.doe@example.com`nSkills: Python, FastAPI`nEducation: BSc Computer Science, Example University, 2022" } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/extract/resume -Method Post -ContentType "application/json" -Body $resume
```

Equivalent curl:

```powershell
curl.exe --% -X POST http://127.0.0.1:8000/extract/resume -H "Content-Type: application/json" -d "{\"text\":\"Jane Doe, jane.doe@example.com, Skills: Python, FastAPI\"}"
```

Expected resume JSON shape (unmentioned fields are null or empty collections):

```json
{
  "name": "Jane Doe",
  "email": "jane.doe@example.com",
  "phone": null,
  "skills": ["Python", "FastAPI"],
  "education": [{"degree": "BSc Computer Science", "institution": "Example University", "year": "2022"}],
  "experience": [],
  "summary": null
}
```

Example invoice text:

```text
Invoice: INV-1001
Date: 2025-01-15
From: Example Supply
To: Acme Ltd
2 x Widget at $12.50: $25.00
Subtotal: $25.00
Tax: $2.50
Total: $27.50 USD
```

PowerShell:

```powershell
$invoice = @{ text = "Invoice: INV-1001`nDate: 2025-01-15`nFrom: Example Supply`nTo: Acme Ltd`n2 x Widget at `$12.50: `$25.00`nSubtotal: `$25.00`nTax: `$2.50`nTotal: `$27.50 USD" } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/extract/invoice -Method Post -ContentType "application/json" -Body $invoice
```

Equivalent curl:

```powershell
curl.exe --% -X POST http://127.0.0.1:8000/extract/invoice -H "Content-Type: application/json" -d "{\"text\":\"Invoice INV-1001. From Example Supply. To Acme Ltd. 2 x Widget at $12.50: $25.00. Subtotal $25.00, tax $2.50, total $27.50 USD.\"}"
```

Expected invoice JSON shape:

```json
{
  "invoice_number": "INV-1001",
  "invoice_date": "2025-01-15",
  "vendor_name": "Example Supply",
  "customer_name": "Acme Ltd",
  "line_items": [{"description": "Widget", "quantity": 2, "unit_price": 12.5, "amount": 25.0}],
  "subtotal": 25.0,
  "tax": 2.5,
  "total_amount": 27.5,
  "currency": "USD"
}
```

## Edge-case handling

| Condition | Behavior |
|---|---|
| Empty or whitespace-only input | HTTP 400; extraction is not called |
| Input longer than `MAX_INPUT_CHARS` (default 20000) | HTTP 413 |
| Rate limit after retries | Up to 3 attempts with exponential backoff, then HTTP 429 |
| Temporary provider outage | Up to 3 attempts, then HTTP 503 |
| Missing API key, model, or unsupported provider | Startup warning; HTTP 500 with a safe configuration message |
| Invalid LLM output | HTTP 422 with Pydantic validation details |
| No relevant data | Empty strings/lists and null optional fields, according to schema |

## Tests

Tests replace the LLM with fakes and need no API key or network access:

```powershell
pytest
```

## Limitations and future improvements

- Extraction quality and supported model capabilities vary by provider and model.
- The service validates structure but does not independently verify extracted facts or accounting arithmetic.
- Consider adding authentication, request quotas, durable audit metrics, and an asynchronous job path before production use.
- Additional document types, locale-aware dates/currencies, and domain-specific validation can be added as requirements evolve.
