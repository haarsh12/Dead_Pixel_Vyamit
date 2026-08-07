# Frontend API contract

The Flutter application and the clean backend use the following routes. Every
non-public route requires `Authorization: Bearer <access_token>`.

| Flutter use | Backend route | Status |
| --- | --- | --- |
| Send OTP | `POST /auth/send-otp` | Implemented; validates Indian mobile input and rate-limits requests. |
| Verify OTP | `POST /auth/verify-otp` | Implemented. |
| Save profile | `PUT /auth/update-profile` | Compatibility route; `/auth/profile` remains the documented route. |
| List/create inventory | `GET` / `POST /items/` | Uses the authenticated user's active shop-category inventory scope; a client cannot choose another scope. |
| Update/delete inventory | `PUT` / `DELETE /items/{id}/` | Uses the trailing-slash-compatible endpoints with owner and active-category isolation. |
| Save/history/dashboard | `POST` / `GET /analytics/bills`, `GET /analytics/dashboard` | Implemented; item totals are verified and customer summaries are updated. |
| Voice inventory | `POST /inventory/voice-parse` | Implemented; Gemini is used when configured and a deterministic parser is available otherwise. |
| Voice HTTP fallback | `POST /voice/process` | Implemented. |
| Continuous voice | `WS /voice/ws/stream?token=<JWT>` | Implemented; accepts `process`, `ping`, and `interrupt`. |
| Doctor prescription voice | `POST /doctor-prescriptions/voice/process`, `WS /doctor-prescriptions/voice/ws/stream?token=<JWT>` | Doctor-only clinical dictation formatter; it is isolated from retail inventory and sales voice processing. |
| Doctor prescription records | `POST /doctor-prescriptions/printed`, `GET /doctor-prescriptions/history` | Immutable records are created after a successful client-side print and are scoped to the authenticated doctor. |
| Doctor patients | `GET /doctor-prescriptions/patients`, `GET /doctor-prescriptions/patients/{id}/prescriptions` | The searchable directory is populated only when the doctor approves the post-print save prompt. |

## WebSocket messages

The client sends `{ "action": "process", "text": "..." }`. The server
responds with `connected`, `processing`, zero or more `stream_token` messages,
and a final `complete` containing the same voice response returned by the HTTP
fallback. Invalid or expired tokens are rejected; the protocol never accepts a
client-supplied user id.

Doctor Prescription uses its own WebSocket route and response shape. It is
available only while the authenticated profile category is `Doctor
Prescription`; its responses use `Cache-Control: no-store` to avoid caching
patient data.

## Runtime configuration

- `DATABASE_URL` is required for data routes. Without it, `/health` and docs
  still start, while data routes return `503` with a setup message.
- `GEMINI_API_KEY` enables embeddings and AI inventory parsing.
- `MISTRAL_API_KEY` optionally enables Mistral before the Gemini fallback.
- `FRONTEND_URL` is a comma-separated CORS origin allow-list for browser builds.
- Flutter release builds require
  `--dart-define=API_BASE_URL=https://your-backend.example`.

## Inventory scope rule

Inventory is a logical namespace per `(authenticated user, profile shop
category)`, not a client-selectable table name. Changing a profile from
Kirana to Hardware loads only the user's Hardware records; the Kirana records
remain stored and become available only when that profile category is selected
again. Voice parsing, voice billing, bulk embedding, RAG retrieval, and RAG
analytics use the same server-side scope, so category data is never mixed in
AI context. Bills and Dashboard totals remain user-wide as requested.
Customer summaries are deliberately excluded from category-specific RAG
prompts until customer records receive the same immutable category snapshot.
