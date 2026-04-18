# Requirements Document

## Introduction

This feature adds real-time Speech-to-Text (STT) capability to the existing full-stack project (FastAPI backend + React/Vite/Tailwind frontend). Users can record audio directly in the browser, which is sent to a new `/transcribe` backend endpoint. The endpoint delegates transcription to the Parakit ASR API and returns the transcribed text as JSON. The transcription result is displayed in the UI and can optionally be piped into the existing text summarizer.

## Glossary

- **ASR_Service**: The Python module (`backend/services/asr_service.py`) responsible for communicating with the Parakit ASR API.
- **Transcribe_Endpoint**: The FastAPI `POST /transcribe` route that accepts audio data and returns transcribed text.
- **SpeechToText_Component**: The React component (`frontend/src/components/SpeechToText.jsx`) that manages browser audio recording and displays transcription results.
- **Parakit_API**: The external Parakit ASR HTTP API used to perform speech-to-text transcription.
- **MediaRecorder**: The browser Web API used to capture microphone audio as a `Blob`.
- **Audio_Blob**: A binary audio payload (WAV or MP3 format) captured by the MediaRecorder and sent to the backend.
- **PARAKIT_API_KEY**: The secret API key stored in the backend `.env` file used to authenticate requests to the Parakit_API.
- **Transcription**: The plain-text string output produced by the Parakit_API from an Audio_Blob input.

---

## Requirements

### Requirement 1: Backend Transcription Endpoint

**User Story:** As a developer, I want a `/transcribe` POST endpoint on the FastAPI backend, so that the frontend can submit audio data and receive a transcription in return.

#### Acceptance Criteria

1. THE Transcribe_Endpoint SHALL accept `multipart/form-data` requests containing an audio file field named `audio` in WAV or MP3 format.
2. WHEN a valid audio file is received, THE Transcribe_Endpoint SHALL delegate transcription to the ASR_Service and return a JSON response with a `transcription` field containing the resulting text.
3. WHEN the audio file field is missing from the request, THE Transcribe_Endpoint SHALL return an HTTP 422 response with a descriptive error message.
4. WHEN the audio file format is not WAV or MP3, THE Transcribe_Endpoint SHALL return an HTTP 415 response with a descriptive error message.
5. THE Transcribe_Endpoint SHALL be registered on the existing FastAPI application instance alongside the `/summarize` endpoint.
6. THE Transcribe_Endpoint SHALL support async execution so that it does not block other concurrent requests.

---

### Requirement 2: ASR Service Module

**User Story:** As a developer, I want a dedicated ASR service module, so that Parakit API communication is encapsulated and independently testable.

#### Acceptance Criteria

1. THE ASR_Service SHALL expose an async function that accepts raw audio bytes and a MIME type string, and returns a Transcription string.
2. WHEN the Parakit_API returns a successful response, THE ASR_Service SHALL extract and return the transcription text from the response payload.
3. WHEN the Parakit_API returns an HTTP error status, THE ASR_Service SHALL raise an exception containing the HTTP status code and the error body returned by the Parakit_API.
4. WHEN a network timeout or connection error occurs, THE ASR_Service SHALL raise an exception with a descriptive message indicating the connectivity failure.
5. THE ASR_Service SHALL read the PARAKIT_API_KEY from the environment at module load time using `python-dotenv` and SHALL NOT accept the key as a function parameter.
6. THE ASR_Service SHALL attach the PARAKIT_API_KEY as an `Authorization: Bearer` header on every request to the Parakit_API.

---

### Requirement 3: Environment Configuration

**User Story:** As a developer, I want API keys stored in environment variables, so that secrets are not hard-coded in source files.

#### Acceptance Criteria

1. THE ASR_Service SHALL load environment variables from `backend/.env` using `python-dotenv` before making any Parakit_API calls.
2. WHEN the `PARAKIT_API_KEY` environment variable is absent or empty at startup, THE ASR_Service SHALL raise a `ValueError` with a message indicating the missing variable.
3. THE backend `.env` file SHALL contain a `PARAKIT_API_KEY` entry and SHALL be listed in `.gitignore` to prevent accidental commits.

---

### Requirement 4: Frontend Recording Component

**User Story:** As a user, I want to record my voice in the browser and see the transcription on screen, so that I can convert speech to text without leaving the application.

#### Acceptance Criteria

1. THE SpeechToText_Component SHALL render a single toggle button that starts microphone recording when the user is not recording and stops recording when the user is recording.
2. WHEN the user activates the start-recording action, THE SpeechToText_Component SHALL request microphone permission via the MediaRecorder API and begin capturing audio.
3. WHEN the user activates the stop-recording action, THE SpeechToText_Component SHALL stop the MediaRecorder, collect the Audio_Blob, and send it to the Transcribe_Endpoint via an HTTP POST request.
4. WHILE a transcription request is in progress, THE SpeechToText_Component SHALL display a loading indicator and disable the toggle button.
5. WHEN the Transcribe_Endpoint returns a successful response, THE SpeechToText_Component SHALL display the Transcription text in a dedicated output area.
6. WHEN the Transcribe_Endpoint returns an error response, THE SpeechToText_Component SHALL display a human-readable error message in the output area.
7. WHEN the browser does not support the MediaRecorder API, THE SpeechToText_Component SHALL display a message informing the user that their browser is not supported.
8. WHEN microphone permission is denied by the user, THE SpeechToText_Component SHALL display a message instructing the user to grant microphone access.

---

### Requirement 5: Recording Status Indicator

**User Story:** As a user, I want a clear visual indicator of the current recording state, so that I always know whether the microphone is active.

#### Acceptance Criteria

1. WHILE recording is active, THE SpeechToText_Component SHALL display a visually distinct recording indicator (e.g., a red animated element) alongside the toggle button.
2. WHILE recording is inactive, THE SpeechToText_Component SHALL display the toggle button in its default visual state with no recording indicator.
3. THE SpeechToText_Component SHALL update the toggle button label to reflect the current state: "Start Recording" when idle and "Stop Recording" when recording.

---

### Requirement 6: Integration with Existing App

**User Story:** As a user, I want the Speech-to-Text panel to appear alongside the existing Text Summarizer, so that I can use both features from a single page.

#### Acceptance Criteria

1. THE App SHALL render the SpeechToText_Component on the main page alongside the existing text summarizer UI.
2. WHEN a Transcription is produced by the SpeechToText_Component, THE App SHALL provide a mechanism for the user to transfer the Transcription text into the summarizer input field.
3. THE App SHALL maintain independent state for the summarizer and the SpeechToText_Component so that actions in one do not reset the other.

---

### Requirement 7: Copy Transcription

**User Story:** As a user, I want to copy the transcription text to my clipboard with one click, so that I can use it in other applications quickly.

#### Acceptance Criteria

1. WHEN a Transcription is displayed, THE SpeechToText_Component SHALL render a "Copy" button adjacent to the transcription output area.
2. WHEN the user activates the Copy button, THE SpeechToText_Component SHALL write the Transcription text to the system clipboard using the browser Clipboard API.
3. WHEN the clipboard write succeeds, THE SpeechToText_Component SHALL display a confirmation message for 2 seconds before reverting to the default Copy button label.
4. WHEN the clipboard write fails, THE SpeechToText_Component SHALL display an error message indicating that the copy operation was unsuccessful.

---

### Requirement 8: Auto-Scroll Transcript Display

**User Story:** As a user, I want the transcription area to automatically scroll to the latest content, so that I do not have to scroll manually when transcriptions are long.

#### Acceptance Criteria

1. WHEN new Transcription text is appended to the output area, THE SpeechToText_Component SHALL automatically scroll the output area to the bottom so the latest text is visible.
2. THE SpeechToText_Component SHALL preserve the scroll position if the user has manually scrolled up, and SHALL resume auto-scroll only when the user scrolls back to the bottom.

---

### Requirement 9: Backend Dependency Management

**User Story:** As a developer, I want all required Python packages declared in a requirements file, so that the backend environment can be reproduced consistently.

#### Acceptance Criteria

1. THE backend `requirements.txt` SHALL list exact pinned versions for `fastapi`, `uvicorn`, `python-dotenv`, `requests`, and `python-multipart`.
2. WHEN a developer installs dependencies using `pip install -r requirements.txt`, THE backend SHALL start without import errors.
