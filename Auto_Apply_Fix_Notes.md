# Auto Job Apply — Naukri Bot Fix Report

## Summary

The Naukri auto-apply bot failed 96 jobs (out of 5,955 logged attempts) with three
errors: **"Apply button not found" (67)**, **"Unanswered recruiter question" (27)**,
and **"Submit failed" (2)**. The run summary in `logs/log.txt` ended with
`Jobs Applied on Naukri: 0 / Failed: 79 / Skipped: 2886`.

Root-cause analysis used the project's own evidence:

- `logs/log.txt` — every questionnaire failure shows the same pattern:
  `Naukri Q [radio]: "What is your Notice Period?" → "40"` followed by
  `Could not select/type recruiter answer: "40"`.
- `logs/screenshots/naukri/*.png` — OCR of the EPAM failure screenshot shows the
  recruiter drawer with radio options **2 weeks / 3 weeks / 1 month / 1.5 month /
  2 months / 3 months**; the Neurealm (walk-in) screenshot shows the page's only
  buttons are **Save** and **"I'm interested"** — there is no Apply button.
- `config/questions.py` — `notice_period = 40` (days).

A second hardening pass (below) fixed five more systemic bugs found in the same
logs: a config-corruption path that silently zeroed `current_experience`
(causing 5,077 wrongful skips), an endless failed-job retry loop (one job was
retried 73 times), skip-noise flooding the failed-jobs CSV (6,710 rows for
1,014 unique jobs), a stuck-pagination loop, and a BOM/duplicate issue in the
unknown-questions log that feeds the dashboard.

## Root causes and fixes

### Bug 1 — Question was extracted but options were ignored (27 failures)

`modules/naukri/questionnaire.py` extracted the question text correctly, then
asked `answer_for_label()` for an answer **without passing the visible options**.
For "What is your Notice Period?" it returned `notice_period` = `"40"` (days),
but the drawer offered radio options in weeks/months. Nothing matched, no option
was clicked, and the job failed as "Unanswered recruiter question".

**Fix — option-aware answering (`modules/naukri/questionnaire.py`):**

- `resolve_answer()` now receives the collected options and always maps the
  answer onto one of them before clicking:
  - `_match_answer_to_option()` — exact/substring/yes-no mapping of a free-form
    answer (config, custom answers, or AI) onto an option.
  - `_best_numeric_option()` + `_parse_option_range()` — numeric reasoning with
    unit conversion (days ⇄ weeks ⇄ months ⇄ years, lakhs): `notice_period = 40`
    now resolves to **"1.5 month"** on the EPAM options, and to **"60 days"** on
    15/30/60/90-day options. Notice period is never understated (40 days never
    claims "1 month"); experience ranges ("3-5 years") and CTC ranges
    ("10-15 Lacs") pick the range containing the configured value.
- `_get_visible_options()` — options are now collected from labels, leaf
  elements and the text next to each radio/checkbox (Naukri renders options as
  `input` + sibling text without `<label for=…>`), filtered against button words
  and the question text.
- Options are only used for selectable questions (radio/checkbox/select); a text
  question's surrounding labels are noise and no longer constrain the answer.
- `_click_option()` — matching moved from XPath string interpolation to
  normalised Python comparison, so case, spacing and quotes in answers cannot
  break the lookup; native inputs are matched via `label[@for]`, ancestor label
  or the input's container text, with an JS-click fallback.
- Native `<select>` dropdowns in the drawer are now handled
  (`_select_native_option()`).
- `_wait_for_answer_selection()` treats a re-rendered/closed drawer as
  registered and verifies filled text fields, selected/active chips.
- Question-loop guard: if the same question does not advance after 3 attempts
  the loop stops cleanly instead of spinning.

### Bug 2 — Dead code with an undefined variable

`_click_save_or_next()` contained a block referencing `targets`, a variable that
does not exist in that function (copy-paste from `_click_option`). If the Save
button lookup ever reached it, the function would raise `NameError`. The block
was misplaced duplicate logic; it was removed.

### Bug 3 — Walk-in jobs have no Apply button (67 failures)

Naukri walk-in postings (e.g. the Neurealm job) replace Apply with
**"I'm interested"**. `APPLY_BUTTON` in `modules/naukri/selectors.py` only
matched Apply/class-apply, so every walk-in job failed with "Apply button not
found" — repeatedly for the same jobs across runs. The selector list now also
matches buttons/links whose visible text contains "interested".

### Bug 4 — Submit clicked page-wide buttons

`submit_application()` searched `FORM_SUBMIT` (Apply/Save/Submit) page-wide. On
chat-only flows there is no standard form, so it could click the job card's
Save/Apply behind the drawer — re-opening the drawer after the questionnaire had
already submitted, producing "Submit failed". Submit (and form filling) are now
scoped to a real application form container; when none exists the chat drawer's
own Save/Continue is treated as the submission. A drawer appearing after submit
is answered instead of failing the application.

### Bug 5 — Form filling fell back to the whole page

`fill_form_fields()` used `find_first(...) or driver`: with no standard form it
cleared and typed answers into unrelated page inputs. It now returns early when
no form container exists.

### Bug 6 — Salary "in lakhs" answered as "0.0"

`_salary_variants()` divided by 100,000 unconditionally. The user's config is
LPA-style (`desired_salary = 25`, `current_ctc = 15`), so a "CTC in lakhs"
question was answered "0.0". Values under 1000 are now treated as already-LPA;
absolute rupee values are still converted.

### Also improved

- `pause_at_unknown_naukri_question = True` now actually prompts (pyautogui) and
  stores the manual answer for future runs; the setting was previously imported
  but never used.
- `MAX_STEPS` raised from 15 to 25 for long questionnaires.
- `_ai_answer()` passes options to all providers (openai/deepseek previously got
  `options=None`/`question_type="text"`).
- AI answers for selectable questions are mapped onto the visible options.
- `click_first()` accepts a `parent` element (used for scoped submits).

## Second pass — systemic bugs found in the same logs

### Bug 7 — Dashboard silently zeroed numeric config (5,077 wrongful skips)

`logs/log.txt` contains **5,077 `Required N > current 0` skip messages and not
one `current 5`** — yet the shipped config says `current_experience = 5`. Every
job needing ≥1 year of experience was skipped as "Experience too high".

The corruption chain: `static/js/dashboard.js` `getFieldValue()` turned an empty
number input into `0` (`el.value ? Number(el.value) : 0`), the dashboard POSTs
the whole section on save, and `modules/config_manager.py:save_config()` wrote
it to `config/search_naukri.py` with no validation. Saving any section with a
blank numeric box (e.g. after a page reload populated nothing) zeroed
`current_experience` (or `experience_min/max`, `max_applications_per_search`, …).

Fixed at both ends:

- **Server (authoritative):** `save_config()` now drops `None`/empty/garbage
  values for a whitelist of numeric fields instead of writing them
  (`_coerce_numeric()` + `NUMERIC_FIELDS`); numeric strings are coerced; a real
  `0` (valid for `notice_period`) still passes.
- **Client:** an empty number box now yields `null` and `collectSection()`
  omits it, so the existing value is kept; `setFieldValue()` no longer erases a
  legitimate `0` (`value || ''` → explicit null check).
- **Startup guard:** `runNaukriBot._sanity_warnings()` prints a loud warning
  when `current_experience = 0` or `experience_min > current_experience`, so a
  future regression is visible immediately instead of silently skipping
  everything.

### Bug 8 — Failed jobs retried forever (67 failures × ~73 attempts)

Only successful applications were remembered (`get_applied_job_keys`); failed
jobs had no memory at all. With `run_non_stop = True` the bot re-opened the same
failing pages every cycle. The shipped failed-CSV proves it: **6,710 rows for
1,014 unique jobs**; the worst job (Scorg International) was attempted **73
times**, each attempt costing a page load, a Gemini call and a screenshot.

Fixed with a persistent retry cap: `jobs_logger.get_failed_job_counts()` counts
past failures per job from the failed-CSV, and the loop gives up on a job once
`historical + this-session failures ≥ failed_job_retry_limit` (new config key,
default 2 = one automatic retry; 0 disables retries, raise it to be more
stubborn). "Already applied" and "external skipped" results are now also added
to the applied-keys set so those pages are not re-opened every cycle.

### Bug 9 — Skip noise buried the failed-jobs history

Every skip wrote a failed-CSV row *and* an activity-log entry — on every cycle.
5,077 of the 6,710 CSV rows are skip records (76%), so the failure analytics
were mostly noise. Skips are now logged once per run (`log_skipped_once()`),
and only to the activity log, not the failed-CSV.

### Bug 10 — Skill extraction burned a Gemini call before every apply

`_extract_skills()` ran on the job description **before** attempting the apply,
so every failed/skipped job still cost an AI call (visible as the "Rate limited
on gemini" spam in the log). Extraction now runs only after a successful
submission, when the value is actually needed for the success row.

### Bug 11 — Stuck pagination re-scanned the same page forever

`go_to_next_page()` "succeeds" even when Naukri serves the same listings again
(the `return_to_search_results` fallback can also land on page 1 while the
internal page counter believes it advanced). The loop now hashes the job IDs of
each results page and stops that search when a page repeats, instead of
re-scanning it until `max_applications_per_search` is reached. Non-stop cycles
are also separated by a configurable cooldown (`nonstop_cycle_gap_minutes`,
default 15) instead of hammering Naukri back-to-back.

### Bug 12 — Unknown-questions log: BOM + duplicates

`logs/naukri_unknown_questions.jsonl` shipped with a UTF-8 BOM on line 1, which
makes `json.loads` fail on that entry (the dashboard endpoint silently dropped
it), and the same question was appended on every encounter. The writer now
emits BOM-free UTF-8 and logs each distinct question once per run; the
dashboard reads with `utf-8-sig` and strips stray BOMs.

## Files changed

| File | Change |
| --- | --- |
| `modules/naukri/questionnaire.py` | Option-aware answering, numeric option matching, robust option collection/clicking, select support, dead-code removal, loop guard, deduped BOM-free unknown-question log |
| `modules/naukri/selectors.py` | "I'm interested" walk-in apply button; dialog-wrapped form container |
| `modules/naukri/apply.py` | Scoped submit, post-submit questionnaire handling, chat-only submission |
| `modules/naukri/forms.py` | Container-scoped filling, LPA-aware salary variants, AI options passthrough |
| `modules/naukri/dom_helpers.py` | `click_first(..., parent=)` support |
| `runNaukriBot.py` | Persistent retry cap, already-applied keying, skip-log dedupe, pagination loop guard, post-success AI extraction, non-stop cooldown, startup sanity warnings |
| `modules/config_manager.py` | Numeric-field validation guard in `save_config()` |
| `modules/jobs_logger.py` | `get_failed_job_counts()` |
| `modules/validator.py` | Checks for the two new config keys |
| `config/search_naukri.py` | New keys: `failed_job_retry_limit = 2`, `nonstop_cycle_gap_minutes = 15` |
| `static/js/dashboard.js` | Empty number field no longer saves as 0; legit 0 no longer renders blank |
| `app.py` | BOM-tolerant unknown-questions read |

No existing config values were changed; `notice_period = 40`, `desired_salary = 25`,
`current_ctc = 15`, `current_experience = 5` and `years_of_experience = '4'`
keep their meaning.

## Verification

`scripts/test_naukri_fix.py` (kept in the archive) runs 58 offline checks with
stubbed selenium against the real modules — no browser or login needed:

1. **Pure logic** (18 checks): range parsing with unit conversion; resolving the
   notice period, experience, CTC, relocate and yes/no questions onto option
   lists; never-understated notice period; text questions unchanged.
2. **Fake-DOM end-to-end** (10 checks): reproduces the exact EPAM failure from
   the logs — a chat drawer with the six notice-period radios and a following
   relocate question. The fixed bot extracts question and options, clicks the
   **1.5 month** radio (not "40"), clicks the drawer Save (never the card's
   Save behind the overlay), advances and closes the drawer.
3. **Selector regression** (4 checks): Apply button matches classic "Apply" and
   walk-in "I'm interested", but not unrelated buttons; dialog forms match.
4. **Native select dropdown** (5 checks): options extracted, right option chosen,
   Save clicked, drawer closes.
5. **Config save guard** (10 checks): the Bug 7 regression — empty/null/garbage
   numeric fields are dropped, numeric strings coerced, legitimate 0 kept,
   non-numeric fields untouched.
6. **Retry cap** (7 checks): `get_failed_job_counts()` parsing and the give-up
   decision (2 failures → skipped, 1+1 → skipped, 0 → retried).
7. **Unknown-question log** (4 checks): dedupe per run, BOM-free writes, and
   BOM'd first line still parses for the dashboard.

`scripts/test_bot_loop.py` adds 6 integration checks that run the real
`apply_to_naukri_jobs()` loop against a scripted world (stubbed browser, search
and AI): a stuck-paginating site is abandoned instead of re-scanned, an
always-failing job stops at the retry limit, a skipped job is logged once, no
Gemini call is spent on failed/skipped jobs, persistent failure memory carries
across runs, and a successful apply triggers exactly one AI extraction.

Result: **58/58 + 6/6 pass**. Against the original code the same fake-DOM
scenario reproduces the production failure verbatim
(`Naukri Q [radio]: "What is your Notice Period?" → "40"` →
`Could not select/type recruiter answer: "40"` → no question answered), proving
the tests target the real defects.

## How to run

Unzip, then as before:

```
pip install -r requirements.txt
python runNaukriBot.py             # or: python app.py  (dashboard)
python scripts/test_naukri_fix.py  # offline self-check (optional)
python scripts/test_bot_loop.py    # offline loop self-check (optional)
```

Note: live Naukri DOMs still evolve — the drawer selectors in
`modules/naukri/selectors.py` remain the place to update class names if Naukri
changes them again.
