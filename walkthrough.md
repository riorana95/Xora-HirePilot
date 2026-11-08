# Walkthrough: Naukri Profile UI & Unknown Questions Discovery

## Summary

Added a dedicated **Naukri Profile** tab to the dashboard with 4 sections: login credentials, personal details, recruiter Q&A editor, and an **unknown questions discovery** feature that surfaces new questions the bot encountered during applications.

Also fixed a pre-existing bug in the config manager where dict values couldn't be saved on Windows due to a CRLF-incompatible regex.

---

## Changes Made

### 1. [app.py](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/app.py)
- Added `json` import
- **`GET /api/naukri/unknown-questions`** — Reads `logs/naukri_unknown_questions.jsonl`, deduplicates by question text, cross-references with existing `custom_naukri_answers` to mark which are already answered vs new
- **`POST /api/naukri/answer-questions`** — Accepts `{answers: {keyword: answer}}`, merges into existing `custom_naukri_answers`, and persists to `config/naukri_questions.py`

### 2. [dashboard.html](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/templates/dashboard.html)
- Added **"Naukri Profile"** tab button with a red notification badge (`unknownBadge`) showing unanswered question count
- Removed the Recruiter Questions card from the Naukri Search tab (moved to Naukri Profile)
- Added new **`panel-naukri-profile`** with 4 cards:
  - **Naukri Login Credentials** — email/password fields
  - **Personal Details for Naukri** — name, phone, city, experience, CTC, notice period, LinkedIn, resume path
  - **Recruiter Questions** — willing to relocate, default yes/no, pause toggle, custom answers textarea
  - **🔔 New Questions Discovered by Bot** — table with question, options, timestamp, status, keyword input, answer input

### 3. [dashboard.js](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/static/js/dashboard.js)
- Added `loadUnknownQuestions()` — fetches from `/api/naukri/unknown-questions`, renders table with editable keyword/answer fields, updates badge count
- Added `saveUnknownAnswers()` — collects filled answers and POSTs to `/api/naukri/answer-questions`, then refreshes
- Added `saveNaukriProfile()` — collects all Naukri Profile fields and saves across `personals`, `questions`, `secrets`, and `naukri_questions` config sections
- Badge auto-loads on startup to show count even before clicking the tab
- Tab switch to "Naukri Profile" auto-triggers `loadUnknownQuestions()`

### 4. [dashboard.css](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/static/css/dashboard.css)
- **`.tab-badge`** — pulsing red notification badge on tab
- **`.unanswered-row`** — amber left-border highlight for new/unanswered questions
- **`.status-new` / `.status-answered`** — orange/green status indicators
- **`.uq-keyword` / `.uq-answer`** — styled inline inputs for the unknown questions table
- **`.status-badge`** — proper header badge style (fixed orphaned CSS)
- Fixed pre-existing orphaned CSS declarations after `.platform-select option`

### 5. [config_manager.py](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/modules/config_manager.py)
- **Bug fix**: Dict regex pattern `\{[\s\S]*?\n\}` failed to match pprint-formatted dicts where `}` is on the same line as the last entry. Simplified to `\{[\s\S]*?\}}` which correctly matches all dict formats.

---

## How It Works

1. **Bot runs** → encounters unknown questions → logs them to `logs/naukri_unknown_questions.jsonl`
2. **User opens dashboard** → "Naukri Profile" tab shows a red badge with count of unanswered questions
3. **User clicks tab** → sees the questions table with question text, options the bot saw, and input fields
4. **User fills in keyword + answer** → clicks "Save Answers" → answers are merged into `config/naukri_questions.py`
5. **Next bot run** → the bot finds answers for previously unknown questions and auto-fills them

---

## Testing

| Test | Result |
|------|--------|
| Flask app imports | ✅ No errors |
| `GET /api/config` | ✅ Returns all sections |
| `GET /api/naukri/unknown-questions` (empty) | ✅ Returns `{total: 0, unanswered: 0}` |
| `GET /api/naukri/unknown-questions` (with data) | ✅ Deduplicates, cross-references, marks status |
| `POST /api/naukri/answer-questions` | ✅ Saves to `config/naukri_questions.py` |
| Dashboard page load | ✅ HTTP 200 |
