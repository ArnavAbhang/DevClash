# Implementation Plan: Speech-to-Text ASR

## Overview

Implement real-time Speech-to-Text capability by adding a Python ASR service module, a FastAPI `/transcribe` endpoint, a `useAudioRecorder` React hook, and a `SpeechToText` React component. The backend uses `httpx` for async Parakit API calls; the frontend uses the MediaRecorder API. Both layers include property-based tests (Hypothesis / fast-check).

## Tasks

- [x] 1. Set up backend dependencies and environment configuration
  - Add `httpx`, `python-dotenv`, `python-multipart`, `pytest`, `pytest-asyncio`, `hypothesis`, and `httpx[test]` to `backend/requirements.txt` with exact pinned versions alongside existing `fastapi`, `uvicorn`
  - Ensure `backend/.env` contains a `PARAKIT_API_KEY` entry and `PARAKIT_API_ENDPOINT` entry (placeholder values are fine)
  - Confirm `backend/.env` is listed in `backend/.gitignore`
  - _Requirements: 3.1, 3.3, 9.1_

- [x] 2. Implement the ASR service module
  - [x] 2.1 Create `backend/services/__init__.py` (empty) and `backend/services/asr_service.py`
    - Call `load_dotenv()` at module load time; read `PARAKIT_API_KEY` and `PARAKIT_API_ENDPOINT` from environment
    - Raise `ValueError("PARAKIT_API_KEY is not set")` if the key is absent or empty
    - Implement `async def transcribe(audio_bytes: bytes, mime_type: str) -> str` using `httpx.AsyncClient`
    - Attach `Authorization: Bearer {PARAKIT_API_KEY}` header on every request
    - On HTTP error: raise `RuntimeError(f"Parakit API error {status_code}: {body}")`
    - On network/timeout error: raise `RuntimeError(f"ASR service unreachable: {detail}")`
    - On success: return `response.json()["transcription"]`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2_

  - [x] 2.2 Write property test — Property 3: ASR service extracts transcription from API response
    - File: `backend/tests/test_asr_service.py`
    - `@given(transcription=st.text())` — mock `httpx.AsyncClient.post` to return a 200 response with `{"transcription": transcription}`; assert `asr_service.transcribe()` returns exactly that string
    - **Property 3: ASR service extracts transcription from API response**
    - **Validates: Requirements 2.1, 2.2**

  - [x] 2.3 Write property test — Property 4: HTTP error propagation with status code
    - File: `backend/tests/test_asr_service.py`
    - `@given(status_code=st.integers(min_value=400, max_value=599))` — mock `httpx` to raise `httpx.HTTPStatusError` with that code; assert `RuntimeError` message contains the status code
    - **Property 4: HTTP error propagation with status code**
    - **Validates: Requirements 2.3**

  - [x] 2.4 Write property test — Property 5: Authorization header on every request
    - File: `backend/tests/test_asr_service.py`
    - `@given(audio_bytes=st.binary(min_size=1), mime_type=st.sampled_from(["audio/wav", "audio/mpeg"]))` — capture the outgoing `httpx` request; assert `Authorization` header equals `Bearer <PARAKIT_API_KEY>`
    - **Property 5: Authorization header on every request**
    - **Validates: Requirements 2.6**

- [x] 3. Implement the `POST /transcribe` endpoint
  - [x] 3.1 Add the `/transcribe` route to `backend/main.py`
    - Import `UploadFile`, `File`, `HTTPException` from FastAPI and import `asr_service`
    - Implement `async def transcribe(audio: UploadFile = File(...)) -> dict`
    - Validate `audio.content_type` against `{"audio/wav", "audio/mpeg"}`; return HTTP 415 with descriptive message on mismatch
    - Read bytes with `await audio.read()`; call `await asr_service.transcribe(audio_bytes, audio.content_type)`
    - Catch `RuntimeError`: map `"unreachable"` → HTTP 503, otherwise → HTTP 502
    - Return `{"transcription": <string>}` on success
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 3.2 Write property test — Property 1: Transcription round-trip
    - File: `backend/tests/test_transcribe_endpoint.py`
    - `@given(audio_bytes=st.binary(min_size=1), transcription=st.text())` — mock `asr_service.transcribe` to return `transcription`; POST a valid WAV file; assert response JSON `transcription` field equals the mocked value
    - **Property 1: Transcription round-trip**
    - **Validates: Requirements 1.1, 1.2**

  - [x] 3.3 Write property test — Property 2: Invalid MIME type rejection
    - File: `backend/tests/test_transcribe_endpoint.py`
    - `@given(mime_type=st.text().filter(lambda m: m not in {"audio/wav", "audio/mpeg"}))` — POST a file with that MIME type; assert HTTP 415 response
    - **Property 2: Invalid MIME type rejection**
    - **Validates: Requirements 1.4**

  - [x] 3.4 Write unit tests for the `/transcribe` endpoint
    - File: `backend/tests/test_transcribe_endpoint.py`
    - Test: missing `audio` field → HTTP 422
    - Test: network timeout from service → HTTP 503
    - Test: Parakit API error from service → HTTP 502
    - _Requirements: 1.3, 1.4_

- [x] 4. Checkpoint — Ensure all backend tests pass
  - Run `pytest backend/tests/` and confirm all tests pass; ask the user if questions arise.

- [ ] 5. Implement the `useAudioRecorder` custom hook
  - [x] 5.1 Create `frontend/src/hooks/useAudioRecorder.js`
    - Manage `MediaRecorder` lifecycle: `getUserMedia`, `start`, chunk collection via `ondataavailable`, `stop`
    - Expose `{ isRecording, startRecording, stopRecording, audioBlob, error }`
    - Set `error` to `"Your browser does not support audio recording."` when `MediaRecorder` is undefined
    - Catch `NotAllowedError` in `getUserMedia` and set `error` to `"Please grant microphone access."`
    - Resolve `audioBlob` as a `Blob` when recording stops
    - _Requirements: 4.1, 4.2, 4.3, 4.7, 4.8_

  - [ ] 5.2 Write property test — Property 6: Recording state drives button label and indicator
    - File: `frontend/src/__tests__/useAudioRecorder.test.js` (or `SpeechToText.test.jsx`)
    - `fc.property(fc.boolean(), ...)` — for any recording state, assert button label is `"Stop Recording"` when recording and `"Start Recording"` when idle; assert recording indicator is present in DOM iff recording is active
    - **Property 6: Recording state drives button label and indicator**
    - **Validates: Requirements 4.1, 5.1, 5.2, 5.3**

- [ ] 6. Implement the `SpeechToText` React component
  - [x] 6.1 Create `frontend/src/components/SpeechToText.jsx`
    - Accept `onTranscription` prop (callback)
    - Use `useAudioRecorder` hook for recording state
    - Render toggle button with label `"Start Recording"` / `"Stop Recording"` based on `isRecording`
    - Show red animated recording indicator while `isRecording` is true (Requirement 5.1)
    - On stop: POST `audioBlob` as `multipart/form-data` to `http://127.0.0.1:8000/transcribe`
    - While request is in-flight: set `isLoading = true`, disable toggle button, show loading indicator (Requirement 4.4)
    - On success: set `transcription` state, call `onTranscription(text)` (Requirement 4.5)
    - On error: set `error` state and display human-readable message (Requirement 4.6)
    - Display `error` from `useAudioRecorder` for unsupported browser / permission denied (Requirements 4.7, 4.8)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 5.1, 5.2, 5.3_

  - [ ] 6.2 Write property test — Property 7: Transcription text displayed in output area
    - File: `frontend/src/components/__tests__/SpeechToText.test.jsx`
    - `fc.property(fc.string({ minLength: 1 }), ...)` — mock `fetch` to return `{ transcription: T }`; trigger stop-recording flow; assert output area text content equals T
    - **Property 7: Transcription text displayed in output area**
    - **Validates: Requirements 4.5**

  - [ ] 6.3 Write unit tests for `SpeechToText.jsx`
    - Renders `"Start Recording"` button initially
    - Shows loading indicator and disabled button while `isLoading` is true
    - Displays error message on API failure
    - Shows unsupported browser message when `MediaRecorder` is undefined
    - Shows permission denied message on `NotAllowedError`
    - _Requirements: 4.1, 4.4, 4.6, 4.7, 4.8_

- [ ] 7. Implement Copy Transcription feature
  - [x] 7.1 Add Copy button and clipboard logic to `SpeechToText.jsx`
    - Render `"Copy"` button adjacent to transcription output area only when `transcription` is non-empty
    - On click: call `navigator.clipboard.writeText(transcription)`
    - On success: set `copyStatus = 'copied'`; revert to `'idle'` after 2 seconds
    - On failure: set `copyStatus = 'error'`; display `"Copy failed"` message
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ] 7.2 Write property test — Property 9: Copy writes correct text to clipboard
    - File: `frontend/src/components/__tests__/SpeechToText.test.jsx`
    - `fc.property(fc.string({ minLength: 1 }), ...)` — set transcription to T; click Copy; assert `navigator.clipboard.writeText` was called with exactly T
    - **Property 9: Copy writes correct text to clipboard**
    - **Validates: Requirements 7.2**

  - [ ] 7.3 Write unit tests for Copy button
    - Copy button appears when transcription is present
    - Confirmation message appears then reverts after 2 seconds on successful copy
    - Copy error message shown on clipboard failure
    - _Requirements: 7.1, 7.3, 7.4_

- [ ] 8. Implement Auto-Scroll transcript display
  - [x] 8.1 Add scroll tracking and auto-scroll logic to `SpeechToText.jsx`
    - Attach `outputRef` to the transcription output `<div>`
    - Attach `scroll` event listener: set `userScrolledRef.current = true` when `scrollTop + clientHeight < scrollHeight`; set to `false` when user scrolls back to bottom
    - In a `useEffect` watching `transcription`: if `userScrolledRef.current === false`, set `outputRef.current.scrollTop = outputRef.current.scrollHeight`
    - _Requirements: 8.1, 8.2_

  - [ ] 8.2 Write property test — Property 10: Auto-scroll behavior based on scroll position
    - File: `frontend/src/components/__tests__/SpeechToText.test.jsx`
    - `fc.property(fc.boolean(), fc.string({ minLength: 1 }), ...)` — for any `userScrolled` flag value and any new transcription string, assert `scrollTop` is set to `scrollHeight` iff `userScrolled` is `false`
    - **Property 10: Auto-scroll behavior based on scroll position**
    - **Validates: Requirements 8.1, 8.2**

- [ ] 9. Integrate `SpeechToText` into `App.jsx` and wire state
  - [x] 9.1 Update `frontend/src/App.jsx`
    - Lift `summarizerText` to `App` state; pass it as `value` to the summarizer `<textarea>`
    - Render `<SpeechToText onTranscription={(t) => setSummarizerText(t)} />` alongside the existing summarizer
    - Ensure summarizer and STT states are independent (STT actions do not reset summarizer and vice versa, unless user clicks "Use in Summarizer")
    - Add a `"Use in Summarizer"` button or rely on the `onTranscription` callback to transfer text
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ] 9.2 Write property test — Property 8: Independent component state
    - File: `frontend/src/components/__tests__/SpeechToText.test.jsx`
    - `fc.property(fc.array(fc.oneof(...)), ...)` — interleave summarizer and STT actions; assert STT internal state is unchanged by summarizer actions and summarizer input is unchanged by STT actions unless `onTranscription` fires
    - **Property 8: Independent component state**
    - **Validates: Requirements 6.3**

  - [ ] 9.3 Write unit tests for App integration
    - Both `SpeechToText` and summarizer components render on the main page
    - `"Use in Summarizer"` / `onTranscription` callback transfers transcription text to summarizer input
    - _Requirements: 6.1, 6.2_

- [x] 10. Set up frontend test infrastructure
  - Install `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, and `fast-check` as dev dependencies in `frontend/package.json` with exact pinned versions
  - Add a `vitest.config.js` (or update `vite.config.js`) to configure the test environment (`jsdom`)
  - Add a `test` script to `frontend/package.json`: `"test": "vitest --run"`
  - _Requirements: 9.1_

- [ ] 11. Final checkpoint — Ensure all tests pass
  - Run `pytest backend/tests/` and `npm run test` in `frontend/`; confirm all tests pass; ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Checkpoints (tasks 4 and 11) ensure incremental validation at natural breaks
- Property tests validate universal correctness properties across arbitrary inputs; unit tests validate specific examples and edge cases
- Task 10 (frontend test infrastructure) should be completed before running any frontend tests
