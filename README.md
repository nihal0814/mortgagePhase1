# Mortgage AI Processing System - Phase 4

A beginner-friendly mortgage application dashboard for a college project. Phase 4 adds deterministic DTI/LTV calculations, document/application comparison, missing-information checks, and human-review flags while preserving Phase 1 CRUD, Phase 2 document extraction, and Phase 3 Nemotron analysis.

## Project structure

```text
mortgage-ai/
├── backend/
│   ├── app/
│   ├── database/
│   ├── models/
│   ├── routes/
│   ├── schemas/
│   ├── services/
│   ├── tests/
│   ├── main.py
│   └── requirements.txt
└── frontend/
    ├── src/
    ├── package.json
    └── ...
```

## Run on Windows PowerShell

Open two PowerShell windows from the project root (`D:\NAT\mortgagePhase1`).

### 1. Start the backend

```powershell
cd .\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs at `http://localhost:8000`. The SQLite database (`mortgage.db`) is created automatically on first startup. Existing application and document data is preserved; `create_all()` adds the document, Nemotron analysis, application summary, and financial validation tables without deleting existing records. Uploaded files are stored privately in `backend/uploads/<application-id>/` and are not exposed as static files. API documentation is available at `http://localhost:8000/docs`.

If PowerShell blocks virtual environment activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. Start the frontend

```powershell
cd .\frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173`.

### 3. Optional OCR setup on Windows

Text-based PDFs work with PyMuPDF and do not need Tesseract. Image OCR and scanned-PDF OCR require Tesseract OCR and Poppler.

1. Install Tesseract OCR for Windows from the official UB Mannheim installer.
2. Install Poppler for Windows and add its `Library\bin` directory to `PATH` for scanned PDFs.
3. If Tesseract is not on `PATH`, copy `.env.example` to `.env` and set:

```text
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

The backend reports a useful failed extraction status when OCR is not installed; it does not crash the API.

### 4. Configure NVIDIA Nemotron

Nemotron calls are made only by the backend. React never receives the API key. Copy the template and set credentials for an approved NVIDIA NIM deployment:

```powershell
cd D:\NAT\mortgagePhase1\backend
Copy-Item .env.example .env
notepad .env
```

Set values similar to:

```text
NVIDIA_API_KEY=your_key_here
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=your-supported-nemotron-model
```

Use the exact model name enabled by your NVIDIA deployment. NVIDIA-hosted NIM and a self-hosted NIM may expose different model names and base URLs. The backend uses the official OpenAI-compatible Python client against NVIDIA NIM's `POST /chat/completions` endpoint. `NVIDIA_USE_JSON_MODE=true` requests JSON mode when the selected model supports it; set it to `false` for a deployment that does not support `response_format` (the prompt still requires JSON and the response is validated). Confirm the selected model supports the endpoint before testing. Never commit `.env` or an API key.

If these values are absent, the application remains fully usable for upload and extraction and shows a clear `AI not configured` error when analysis is requested.

Document text is sensitive. Use an approved NVIDIA deployment and review its data-handling, retention, and network settings before sending borrower documents. The application does not send original files, only extracted text, and does not log prompts or extracted content.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Health check |
| GET | `/applications` | List applications; accepts `search` and `status` query parameters |
| POST | `/applications` | Create an application |
| GET | `/applications/{id}` | Get one application |
| PUT | `/applications/{id}` | Edit application details |
| PATCH | `/applications/{id}/status` | Change status |
| POST | `/applications/{application_id}/documents` | Upload a PDF or image |
| GET | `/applications/{application_id}/documents` | List application documents |
| GET | `/applications/{application_id}/documents/{document_id}` | Get document metadata |
| PUT | `/applications/{application_id}/documents/{document_id}` | Change document category |
| DELETE | `/applications/{application_id}/documents/{document_id}` | Delete metadata and stored file |
| POST | `/applications/{application_id}/documents/{document_id}/extract` | Extract or re-extract text |
| GET | `/applications/{application_id}/documents/{document_id}/text` | Read extracted text |
| POST | `/applications/{application_id}/documents/{document_id}/analyze` | Analyze extracted text with Nemotron |
| GET | `/applications/{application_id}/documents/{document_id}/analysis` | Retrieve document analysis |
| POST | `/applications/{application_id}/analyze` | Summarize completed document analyses |
| GET | `/applications/{application_id}/analysis` | Retrieve application summary |
| GET | `/ai/status` | Show provider/model configuration without exposing the API key |
| POST | `/applications/{application_id}/validate` | Run deterministic financial validation |
| GET | `/applications/{application_id}/validation` | Retrieve financial validation |
| GET | `/applications/{application_id}/validation/issues` | List validation issues |
| POST | `/applications/{application_id}/validation/recalculate` | Recalculate validation from current data |
| POST | `/policies` | Upload, extract, chunk, and index a demonstration policy |
| GET | `/policies` | List policy versions |
| DELETE | `/policies/{policy_id}` | Delete a policy and its index entries |
| POST | `/policies/search` | Retrieve relevant active policy chunks |
| POST | `/applications/{application_id}/policy-analysis` | Generate evidence-grounded policy explanation |
| POST | `/applications/{application_id}/underwriting/run` | Run bounded underwriting-support workflow |
| GET | `/applications/{application_id}/underwriting/status` | Get latest workflow status |
| GET | `/applications/{application_id}/underwriting/events` | Get high-level audit events |
| GET | `/applications/{application_id}/underwriting/report` | Get validated underwriting report |

## Test the features

1. Open **New Application**, submit the required borrower and financial fields, and confirm the success message.
2. Confirm the new record appears in the dashboard cards and Recent applications table.
3. Open **Applications**, search by borrower name or generated application ID, and filter by each status.
4. Open a record, edit a field, and choose **Save changes**.
5. Change its status in the details page and confirm the dashboard count changes.
6. On the details page, choose a category and upload a valid PDF or PNG/JPG. Confirm the file name, type, size, date, and Uploaded status appear.
7. Change the category, delete the document, and confirm it disappears from the list.
8. Upload a text-based PDF, choose Extract text, then View text and Copy text. Check the page labels and the extraction warning.
9. Configure NVIDIA credentials, then click Analyze with Nemotron. Confirm structured fields, summary, missing information, review flags, source references, and the `AI-generated — verify against original documents` label.
10. Click Summarize application after at least one document analysis succeeds. Confirm the document-derived borrower/income overview, coverage, conflicts, missing information, review flags, and source document IDs.
11. Open Financial analysis and click **Run financial validation**. Confirm DTI, LTV, income, debt, loan, and property cards are calculated by the backend.
12. Compare a salary document with a different application income and confirm a discrepancy row, percentage difference, severity, and source document ID.
13. Try a loan amount greater than property value and confirm a Needs Review issue, not automatic rejection.
14. Configure `MAX_DTI`, `MAX_LTV`, or `MIN_CREDIT_SCORE` and confirm the result says Policy Review Required, not approved/rejected.
15. Without NVIDIA credentials, confirm upload, extraction, and deterministic financial validation still work.
16. Upload an image or scanned PDF with OCR configured, then extract it. Without OCR configured, confirm the document shows Failed with a setup message rather than crashing the API.
17. Try a `.txt`, empty, corrupt, or oversized file and confirm the API rejects it or marks extraction as Failed.
18. Try document endpoints with an application ID from another record and confirm they return 404.
19. Try a negative financial value or blank required field and confirm the form shows validation feedback.
20. Run the automated tests:

```powershell
cd .\backend
pytest
```

The tests mock the NIM client and never require a real NVIDIA API key.

## Financial validation configuration

```text
FINANCIAL_TOLERANCE_PERCENT=2
MAX_DTI=
MAX_LTV=
MIN_CREDIT_SCORE=
```

The tolerance is a software comparison threshold. It is not a lending-policy requirement. Optional maximum DTI, maximum LTV, and minimum credit score values only create `Policy Review Required` flags and never approve or reject an application.

## Phase 5 policy RAG

The Policy Knowledge Base is a small local RAG demonstration. PDF/TXT policy files are stored separately from borrower uploads, extracted into page-aware chunks, embedded with a dependency-free local hashed word/n-gram embedding, and stored in a private JSON vector index. Policy metadata and chunk text remain in SQLite. The vector-store API is isolated so it can later be replaced with FAISS, Chroma, or a hosted embedding service without changing the routes.

Upload only approved demonstration material. The included [sample policy](sample_policies/sample_mortgage_underwriting_guidelines.txt) is explicitly **Sample / Demonstration Policy** and is not a law, regulation, or actual lender policy.

Basic workflow:

1. Open **Policy Knowledge Base**.
2. Upload the sample TXT file (or a PDF) with title, category, version, and optional effective date.
3. Search for `What is the DTI requirement?` and inspect page/section evidence.
4. Create an application, run financial validation, then open **Analyze against policy**.
5. Configure NVIDIA credentials if Nemotron explanation is desired. Without credentials, retrieval remains available and the response clearly reports that AI is unavailable.
6. Verify every policy citation and calculation against the original policy. The system never approves or rejects a loan.

Phase 5 variables:

```text
MAX_POLICY_UPLOAD_SIZE=10485760
POLICY_UPLOADS_DIR=C:\path\to\private\policy_uploads
POLICY_INDEX_PATH=C:\path\to\private\policy_index.json
POLICY_CHUNK_SIZE=1200
POLICY_CHUNK_OVERLAP=150
POLICY_EMBEDDING_DIMENSIONS=256
POLICY_TOP_K=5
```

The first implementation intentionally uses a local hashed embedding rather than downloading a large model. It is suitable for a college demonstration, deterministic in tests, and not a substitute for production-quality semantic embeddings.

## Phase 6 agentic underwriting workflow

The **AI Underwriting Assistant** is one controlled backend orchestrator. It has a maximum of 15 tool steps and calls existing Python services for document extraction, Nemotron document analysis, financial validation, and policy retrieval. It does not access raw SQL or arbitrary filesystem paths, does not expose chain-of-thought, and never approves or rejects a loan.

Run it from an application details page with **Run AI underwriting review**, or call:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/applications/APP-ID/underwriting/run |
  ConvertTo-Json -Depth 10
```

The result is persisted as an audit run with high-level events such as document checking, financial validation, policy retrieval, summary generation, and failures. The report always includes `human_review_required: true`. Missing evidence, failed extraction, unavailable policy retrieval, or model errors produce `Needs Attention` rather than a silent or automated lending decision.

To check the local configuration without exposing the key:

```powershell
Invoke-RestMethod http://localhost:8000/ai/status | ConvertTo-Json
```

Then perform the real hosted-NIM smoke test by uploading and extracting a small text PDF and clicking **Analyze with Nemotron**. A `Completed` result confirms the configured API key, base URL, model, endpoint, and response parsing are working. Authentication, rate-limit, timeout, provider, and malformed-response errors are shown without logging the key or document text.

14. Visit `http://localhost:8000/docs` to exercise the backend endpoints directly if needed.

## Production build check

```powershell
cd .\frontend
npm run build
```
