# Frontend API contract

The Flutter application and the clean backend use the following routes. Every
non-public route requires `Authorization: Bearer <access_token>`.

| Flutter use | Backend route | Status |
| --- | --- | --- |
| Send OTP | `POST /auth/send-otp` | Implemented; validates Indian mobile input and rate-limits requests. |
| Verify OTP | `POST /auth/verify-otp` | Implemented. |
| Save profile | `PUT /auth/update-profile` | Compatibility route; `/auth/profile` remains the documented route. |
| List/create inventory | `GET` / `POST /items/` | Implemented. |
| Update/delete inventory | `PUT` / `DELETE /items/{id}/` | Implemented with the Flutter trailing slash and owner isolation. |
| Save/history/dashboard | `POST` / `GET /analytics/bills`, `GET /analytics/dashboard` | Implemented; item totals are verified and customer summaries are updated. |
| Voice inventory | `POST /inventory/voice-parse` | Implemented; Gemini is used when configured and a deterministic parser is available otherwise. |
| Voice HTTP fallback | `POST /voice/process` | Implemented. |
| Continuous voice | `WS /voice/ws/stream?token=<JWT>` | Implemented; accepts `process`, `ping`, and `interrupt`. |

## WebSocket messages

The client sends `{ "action": "process", "text": "..." }`. The server
responds with `connected`, `processing`, zero or more `stream_token` messages,
and a final `complete` containing the same voice response returned by the HTTP
fallback. Invalid or expired tokens are rejected; the protocol never accepts a
client-supplied user id.

## Runtime configuration

- `DATABASE_URL` is required for data routes. Without it, `/health` and docs
  still start, while data routes return `503` with a setup message.
- `GEMINI_API_KEY` enables embeddings and AI inventory parsing.
- `MISTRAL_API_KEY` optionally enables Mistral before the Gemini fallback.
- `FRONTEND_URL` is a comma-separated CORS origin allow-list for browser builds.
- Flutter release builds require
  `--dart-define=API_BASE_URL=https://your-backend.example`.
