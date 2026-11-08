'''
Develop by Rana Rahul

Review log for AI-answered Naukri recruiter questions.

Every question the AI answers during an application is appended here so you can
later mark it correct or wrong from the dashboard. Marking one wrong and
teaching the right keyword:answer pair writes the pair into
custom_naukri_answers, so the bot answers that question itself from then on.
'''

import json
from datetime import datetime
from pathlib import Path

from config.settings import logs_folder_path
from modules.helpers import print_lg

AI_ANSWERS_LOG = Path(logs_folder_path) / "naukri_ai_answers.jsonl"

VALID_FEEDBACK = ("pending", "correct", "wrong")


def record_ai_answer(question: str, answer: str, options: list | None = None,
                     source: str = "questionnaire") -> None:
    '''Append one AI-answered question (one row per occurrence).'''
    if not question or not answer:
        return
    try:
        AI_ANSWERS_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "question": question,
            "answer": answer,
            "options": options or [],
            "source": source,
            "feedback": "pending",
            "time": datetime.now().isoformat(),
        }
        with open(AI_ANSWERS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print_lg("Could not record AI answer:", e)


def _read_all() -> list[dict]:
    entries: list[dict] = []
    if not AI_ANSWERS_LOG.exists():
        return entries
    try:
        with open(AI_ANSWERS_LOG, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip().lstrip("\ufeff")
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print_lg("Could not read AI answers log:", e)
    return entries


def get_ai_answers() -> list[dict]:
    '''Deduplicated list, newest occurrence first.

    A question keeps its decided feedback once you set it; new occurrences of
    the same question do not reset it. `count` says how often the AI met it.'''
    entries = _read_all()
    by_question: dict[str, dict] = {}
    for e in entries:
        q = (e.get("question") or "").strip()
        if not q:
            continue
        decided = e.get("feedback") in ("correct", "wrong")
        existing = by_question.get(q)
        if existing is None:
            by_question[q] = {
                "question": q,
                "answer": e.get("answer", ""),
                "options": e.get("options", []),
                "feedback": e.get("feedback", "pending"),
                "count": 1,
                "last_time": e.get("time", ""),
                "keyword": e.get("keyword", ""),
            }
        else:
            existing["count"] += 1
            if e.get("time", "") > existing["last_time"]:
                existing["last_time"] = e.get("time", "")
                existing["answer"] = e.get("answer", existing["answer"])
                existing["options"] = e.get("options", existing["options"])
            if decided and existing["feedback"] == "pending":
                existing["feedback"] = e["feedback"]
            if e.get("keyword"):
                existing["keyword"] = e["keyword"]
    result = sorted(by_question.values(), key=lambda d: d["last_time"], reverse=True)
    return result


def set_feedback(question: str, feedback: str) -> bool:
    '''Mark every occurrence of a question as correct/wrong.'''
    if feedback not in VALID_FEEDBACK:
        return False
    entries = _read_all()
    changed = False
    for e in entries:
        if (e.get("question") or "").strip() == (question or "").strip():
            e["feedback"] = feedback
            changed = True
    if changed:
        _write_all(entries)
    return changed


def set_keyword(question: str, keyword: str) -> bool:
    '''Remember the keyword pair taught for a question (shown in the UI).'''
    entries = _read_all()
    changed = False
    for e in entries:
        if (e.get("question") or "").strip() == (question or "").strip():
            e["keyword"] = keyword
            changed = True
    if changed:
        _write_all(entries)
    return changed


def _write_all(entries: list[dict]) -> None:
    try:
        AI_ANSWERS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(AI_ANSWERS_LOG, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    except Exception as ex:
        print_lg("Could not update AI answers log:", ex)


def seed_from_log_txt(log_txt_path) -> int:
    '''Backfill AI answers from an existing logs/log.txt.

    Parses the `Asking Gemini to answer Naukri question: X` /
    `Gemini answered: "Y"` pairs the bot has always printed (config-sourced
    answers like the notice period never appear there), so the review page
    starts with real history instead of empty.'''
    path = Path(log_txt_path)
    if not path.exists():
        return 0
    # Skip if the JSONL already has content (seed only once).
    if _read_all():
        return 0
    import re
    ask = re.compile(r'Asking (?:Gemini|AI) to answer Naukri question: (.+)')
    ans = re.compile(r'^(?:Gemini|AI) answered: "(.*)"')
    seen: dict[str, dict] = {}
    pending_question = None
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n")
                m = ask.search(line)
                if m:
                    pending_question = m.group(1).strip()
                    continue
                if pending_question:
                    m = ans.match(line.strip())
                    if m:
                        answer = m.group(1).strip()
                        if answer:
                            item = seen.setdefault(pending_question, {"question": pending_question, "answer": answer, "count": 0})
                            item["count"] += 1
                        pending_question = None
    except Exception as e:
        print_lg("Could not seed AI answers from log.txt:", e)
        return 0
    for item in seen.values():
        for _ in range(min(item["count"], 50)):
            record_ai_answer(item["question"], item["answer"], source="log.txt seed")
    return len(seen)
