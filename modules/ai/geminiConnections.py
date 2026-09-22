import google.generativeai as genai
import time
from config.secrets import llm_model, llm_api_key
from config.settings import showAiErrorAlerts
from modules.helpers import print_lg, critical_error_log, convert_to_json
from modules.ai.prompts import *
from pyautogui import confirm
from typing import Literal


# ── Dual-model fallback system ──────────────────────────────────────────────
# Primary model: fast + smart (gemini-3.6-flash)
# Fallback model: lighter + higher free-tier limits (gemini-3.5-flash-lite)
# When one model hits rate limits, the other takes over automatically.
FALLBACK_MODEL_NAME = "gemini-3.5-flash-lite"
_fallback_model = None          # Lazy-initialized on first rate limit
_active_model_name = llm_model  # Track which model is currently in use
_rate_limited_until = {}        # {model_name: timestamp} — when rate limit expires
_request_count = 0              # Total requests, used for alternating

def gemini_get_models_list():
    """
    Lists available Gemini models that support content generation.
    """
    try:
        print_lg("Getting Gemini models list...")
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        print_lg("Available models:")
        for model in models:
            print_lg(f"- {model}")
        return models
    except Exception as e:
        critical_error_log("Error occurred while getting Gemini models list!", e)
        return ["error", e]

def gemini_create_client():
    """
    Configures the Gemini client and validates the selected model.
    * Returns a configured Gemini model object or None if an error occurs.
    """
    try:
        print_lg("Configuring Gemini client...")
        if not llm_api_key or "YOUR_API_KEY" in llm_api_key:
            raise ValueError("Gemini API key is not set. Please set it in `config/secrets.py`.")
        
        genai.configure(api_key=llm_api_key)
        
        models = gemini_get_models_list()
        if "error" in models:
            raise ValueError(models[1])
        if not any(llm_model in m for m in models):
             raise ValueError(f"Model `{llm_model}` is not found or not available for content generation!")

        model = genai.GenerativeModel(llm_model)
        
        print_lg("---- SUCCESSFULLY CONFIGURED GEMINI CLIENT! ----")
        print_lg(f"Using Model: {llm_model}")
        print_lg("Check './config/secrets.py' for more details.\n")
        print_lg("---------------------------------------------")
        
        return model
    except Exception as e:
        error_message = f"Error occurred while configuring Gemini client. Make sure your API key and model name are correct."
        critical_error_log(error_message, e)
        try:
            from modules.helpers import is_headless
            if not is_headless() and showAiErrorAlerts:
                if "Pause AI error alerts" == confirm(f"{error_message}\n{str(e)}", "Gemini Connection Error", ["Pause AI error alerts", "Okay Continue"]):
                    pass  # alerts already logged
        except Exception:
            pass
        return None

def _get_fallback_model():
    """Lazily create the fallback model on first use."""
    global _fallback_model
    if _fallback_model is None:
        try:
            _fallback_model = genai.GenerativeModel(FALLBACK_MODEL_NAME)
            print_lg(f"Fallback model initialized: {FALLBACK_MODEL_NAME}")
        except Exception as e:
            print_lg(f"Could not initialize fallback model: {e}")
    return _fallback_model


def _pick_model(primary_model):
    """
    Pick which model to use for this request.
    Strategy: alternate every 3 requests to spread load, but skip
    any model that is currently rate-limited.
    """
    global _request_count, _active_model_name
    _request_count += 1
    now = time.time()

    primary_blocked = _rate_limited_until.get(llm_model, 0) > now
    fallback = _get_fallback_model()
    fallback_blocked = _rate_limited_until.get(FALLBACK_MODEL_NAME, 0) > now

    if primary_blocked and fallback and not fallback_blocked:
        _active_model_name = FALLBACK_MODEL_NAME
        return fallback
    if fallback_blocked or not fallback:
        _active_model_name = llm_model
        return primary_model
    # Alternate: use primary for 3 requests, then fallback for 3
    if (_request_count % 6) < 3:
        _active_model_name = llm_model
        return primary_model
    else:
        _active_model_name = FALLBACK_MODEL_NAME
        return fallback


def gemini_completion(model, prompt: str, is_json: bool = False) -> dict | str:
    """
    Generates content using Gemini with automatic model fallback.
    If the active model hits a 429 rate limit, retries with the other model.
    """
    if not model:
        raise ValueError("Gemini client is not available!")

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    # Try with the smartly-picked model first, then fallback on 429
    chosen = _pick_model(model)
    models_to_try = [chosen]

    # Add the other model as fallback
    fallback = _get_fallback_model()
    if chosen is model and fallback:
        models_to_try.append(fallback)
    elif chosen is fallback:
        models_to_try.append(model)

    for attempt_model in models_to_try:
        try:
            model_name = getattr(attempt_model, '_model_name', _active_model_name)
            print_lg(f"Calling Gemini API ({model_name})...")
            response = attempt_model.generate_content(prompt, safety_settings=safety_settings)

            if not response.parts:
                raise ValueError("Empty response from Gemini API — safety filter may have blocked it.")

            result = response.text

            if is_json:
                if result.startswith("```json"):
                    result = result[7:]
                if result.endswith("```"):
                    result = result[:-3]
                return convert_to_json(result)

            return result

        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                # Rate limited — mark this model as blocked and try the other
                blocked_name = FALLBACK_MODEL_NAME if attempt_model is fallback else llm_model
                _rate_limited_until[blocked_name] = time.time() + 65  # Block for 65 seconds
                print_lg(f"Rate limited on {blocked_name}, trying alternate model...")
                continue
            else:
                critical_error_log("Error occurred while getting Gemini completion!", e)
                return {"error": error_str}

    # Both models failed
    critical_error_log("Both Gemini models rate-limited!", "Waiting 60s before next attempt.")
    return {"error": "Both models rate-limited. Will retry on next question."}

def gemini_extract_skills(model, job_description: str) -> list[str] | None:
    """
    Extracts skills from a job description using the Gemini model.
    * Takes in `model` - The Gemini model object.
    * Takes in `job_description` of type `str`.
    * Returns a `dict` object representing JSON response.
    """
    try:
        print_lg("Extracting skills from job description using Gemini...")
        prompt = extract_skills_prompt.format(job_description) + "\n\nImportant: Respond with only the JSON object, without any markdown formatting or other text."
        return gemini_completion(model, prompt, is_json=True)
    except Exception as e:
        critical_error_log("Error occurred while extracting skills with Gemini!", e)
        return {"error": str(e)}

def gemini_answer_question(
    model,
    question: str, options: list[str] | None = None, 
    question_type: Literal['text', 'textarea', 'single_select', 'multiple_select'] = 'text', 
    job_description: str = None, about_company: str = None, user_information_all: str = None
) -> str:
    """
    Answers a question using the Gemini API.
    """
    try:
        print_lg(f"Answering question using Gemini AI: {question}")
        user_info = user_information_all or ""
        prompt = ai_answer_prompt.format(user_info, question)

        if options and (question_type in ['single_select', 'multiple_select']):
            options_str = "OPTIONS:\n" + "\n".join([f"- {option}" for option in options])
            prompt += f"\n\n{options_str}"
            if question_type == 'single_select':
                prompt += "\n\nPlease select exactly ONE option from the list above."
            else:
                prompt += "\n\nYou may select MULTIPLE options from the list above if appropriate."
        
        if job_description:
            prompt += f"\n\nJOB DESCRIPTION:\n{job_description}"
        
        if about_company:
            prompt += f"\n\nABOUT COMPANY:\n{about_company}"

        return gemini_completion(model, prompt)
    except Exception as e:
        critical_error_log("Error occurred while answering question with Gemini!", e)
        return {"error": str(e)}

def gemini_answer_naukri_question(
    model,
    question: str,
    options: list[str] | None = None,
    question_type: str = 'text',
    job_description: str = '',
    user_information: str = '',
) -> str:
    """
    Answer a Naukri recruiter question using Gemini AI.
    Returns a clean answer string ready to be typed/selected.
    """
    try:
        from modules.ai.prompts import naukri_question_prompt, naukri_question_with_options_suffix
        
        options_text = ""
        if options:
            options_text = naukri_question_with_options_suffix.format(
                "\n".join(f"- {opt}" for opt in options)
            )
        
        prompt = naukri_question_prompt.format(
            user_information or "Not provided",
            job_description[:2000] if job_description else "Not provided",
            question,
            options_text,
        )
        
        print_lg(f"Asking Gemini to answer Naukri question: {question}")
        result = gemini_completion(model, prompt)
        
        if isinstance(result, dict) and 'error' in result:
            print_lg(f"Gemini error answering question: {result['error']}")
            return ""
        
        # Clean the response
        answer = str(result).strip().strip('"').strip("'").strip()
        # Remove common AI prefixes
        for prefix in ['Answer:', 'answer:', 'A:', 'Response:', 'response:']:
            if answer.startswith(prefix):
                answer = answer[len(prefix):].strip()
        
        # If options were provided, try to match the answer to an option
        if options:
            answer_lower = answer.lower()
            for opt in options:
                if opt.lower() == answer_lower or opt.lower() in answer_lower or answer_lower in opt.lower():
                    answer = opt
                    break
        
        print_lg(f"Gemini answered: \"{answer}\"")
        return answer
    except Exception as e:
        critical_error_log("Error in gemini_answer_naukri_question", e)
        return ""
