# Naukri Auto-Apply: Configuration Guide

## 📁 Config Files At a Glance

| What | File | Purpose |
|---|---|---|
| 🔍 Search & Filters | [`config/search_naukri.py`](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/config/search_naukri.py) | Job titles, locations, experience range, salary, skip rules |
| 💬 Recruiter Q&A | [`config/naukri_questions.py`](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/config/naukri_questions.py) | Custom answers for Naukri chat questions |
| 📝 General Answers | [`config/questions.py`](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/config/questions.py) | Experience, CTC, notice period, resume, LinkedIn |
| 🔑 Login & AI | [`config/secrets.py`](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/config/secrets.py) | Email, password, Gemini API key |
| ⚙️ Bot Settings | [`config/settings.py`](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/config/settings.py) | Headless mode, speed |

---

## 1️⃣ Your Personal Details → [`config/questions.py`](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/config/questions.py)

This is where you configure **your** information that gets filled into application forms:

```python
years_of_experience = '4'           # Line 18 — "How many years of experience?"
current_ctc = 800000                # Line 50 — "What is your current CTC?" (in ₹)
desired_salary = 1800000            # Line 38 — "What is your expected CTC?" (in ₹)
notice_period = 0                   # Line 65 — "Notice period in days?" (0 = immediate)
recent_employer = 'Digit Insurance' # Line 106 — "Current employer?"
confidence_level = '8'              # Line 109 — "Rate yourself 1-10"
require_visa = 'No'                 # Line 21
linkedIn = 'https://...'           # Line 27
```

> [!TIP]
> **CTC is smart** — If the question says "in lakhs", it auto-converts: `800000` → `"8.00"`. If it says "monthly", it divides by 12.

---

## 2️⃣ Naukri-Specific Q&A → [`config/naukri_questions.py`](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/config/naukri_questions.py)

This is the **most important file** for Naukri recruiter chat questions. The bot uses **substring matching** — if the question text contains the key, it uses the value as the answer.

```python
custom_naukri_answers = {
    'bangalore': 'yes',              # "Are you willing to relocate to Bangalore?" → yes
    'current ctc': '13',             # "What is your current CTC?" → 13
    'expected ctc': '17',            # "What is your expected CTC?" → 17
    'notice period': '30',           # "What is your notice period?" → 30
    'total experience': '4',         # "Total years of experience?" → 4
    'years of experience': '4',      # "Years of experience in Angular?" → 4
    'relocate': 'yes',               # Any question with "relocate" → yes
    'immediate joiner': 'yes',       # "Are you an immediate joiner?" → yes
    'serving notice': 'no',          # "Are you serving notice?" → no
    ...
}
```

> [!IMPORTANT]
> **To add a new answer**, just add a new line to this dictionary. The key is a **case-insensitive substring** matched against the question text.
>
> Example: If recruiter asks *"Do you have experience with AWS?"*, add:
> ```python
> 'aws': 'yes',
> ```

---

## 3️⃣ Search & Filters → [`config/search_naukri.py`](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/config/search_naukri.py)

```python
search_terms = ['Angular Developer', 'Full Stack']   # Job titles to search
search_locations = ['Bengaluru']                       # Cities
experience_min = 3                                     # Min years filter
experience_max = 4                                     # Max years filter
salary_min_lpa = 0                                     # Min salary in LPA (0 = skip)
salary_max_lpa = 0                                     # Max salary in LPA (0 = skip)
work_mode = []                                         # ['Remote', 'Hybrid', 'Office']
job_age_days = 7                                       # Only jobs posted in last 7 days
bad_title_words = ['.net', 'python', 'C#']            # Skip these job titles
max_applications_per_search = 50                       # Max per keyword+city
run_non_stop = True                                    # Keep cycling searches
```

---

## 4️⃣ How Unknown Questions Are Handled

The answer resolution chain works like this:

```
1. Check custom_naukri_answers (substring match)     → Found? Use it ✅
2. Check answer_for_label (form-field matching)       → Found? Use it ✅
3. Ask Gemini AI (with job description + your profile) → Got answer? Use it ✅
4. AI also SAVES the answer to custom_naukri_answers   → Next time, step 1 catches it ✅
5. If AI fails too → use default ("Yes" for yes/no, "4" for numbers)
```

### Where unknown questions are saved

When a question has no config match and AI answers it:
- **AI answers are auto-saved** to `custom_naukri_answers` in memory (used for the rest of the session)
- Questions are **logged** to [`logs/naukri_unknown_questions.jsonl`](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/logs/naukri_unknown_questions.jsonl)

### How to review and fix answers manually

1. Open [`logs/naukri_unknown_questions.jsonl`](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/logs/naukri_unknown_questions.jsonl) — each line is a question the bot didn't have a config answer for
2. For any question where AI gave a wrong answer, add the correct answer to [`config/naukri_questions.py`](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/config/naukri_questions.py):
   ```python
   custom_naukri_answers = {
       ...existing entries...,
       'some keyword from the question': 'your correct answer',
   }
   ```
3. Next run, the bot uses your configured answer (step 1) — no AI needed

### Full activity log for cross-verification

Every application attempt is logged to [`logs/naukri_activity_log.jsonl`](file:///f:/My%20App/Xora/Auto_job_applier_linkedIn%20-%20Copy%20(8)/logs/naukri_activity_log.jsonl) with:
- Job title, company, location, link
- All questions asked and answers given
- Whether AI or config answered each question
- Resume used, timestamp, search term

---

## Quick Reference: What to Change for Common Scenarios

| I want to... | Edit this |
|---|---|
| Change years of experience | `questions.py` line 18: `years_of_experience = '4'` |
| Change expected CTC | `naukri_questions.py`: `'expected ctc': '17'` |
| Change current CTC | `naukri_questions.py`: `'current ctc': '13'` |
| Change notice period | `naukri_questions.py`: `'notice period': '30'` |
| Add new job titles to search | `search_naukri.py` line 10: `search_terms = [...]` |
| Add new cities | `search_naukri.py` line 13: `search_locations = [...]` |
| Skip certain job titles | `search_naukri.py` line 63: `bad_title_words = [...]` |
| Answer a specific recruiter question | `naukri_questions.py`: add to `custom_naukri_answers` |
| Change login credentials | `secrets.py` lines 13-14 |
| Switch AI model | `secrets.py` line 59: `llm_model = '...'` |
