'''
Develop by Rana Rahul

Profile Manager — CRUD operations for user profiles.
'''
import os
import json
import re
import copy
from datetime import datetime
from pathlib import Path
import importlib

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_PROFILE = {
    "id": "",
    "name": "",
    "created": "",
    "identity": {
        "first_name": "", "middle_name": "", "last_name": "",
        "phone_number": "", "current_city": "",
        "street": "", "state": "", "zipcode": "", "country": "",
        "gender": "", "ethnicity": "",
        "disability_status": "No", "veteran_status": "No",
    },
    "credentials": {
        "linkedin_email": "", "linkedin_password": "",
        "naukri_email": "", "naukri_password": "",
    },
    "professional": {
        "years_of_experience": "", "current_ctc": 0, "desired_salary": 0,
        "notice_period": 0, "recent_employer": "",
        "linkedIn": "", "website": "",
        "default_resume_path": "all resumes/default/resume.pdf",
        "linkedin_headline": "", "linkedin_summary": "",
        "cover_letter": "", "user_information_all": "",
        "confidence_level": "8",
    },
    "qa": {
        "require_visa": "No", "us_citizenship": "",
        "willing_to_relocate": "Yes", "default_yes_no_answer": "Yes",
        "pause_at_unknown_naukri_question": False,
        "pause_before_submit": False, "pause_at_failed_question": False,
        "overwrite_previous_answers": True,
        "custom_naukri_answers": {},
    },
}

def _profiles_dir() -> Path:
    d = PROJECT_ROOT / 'profiles'
    d.mkdir(exist_ok=True)
    return d

def _index_path() -> Path:
    return _profiles_dir() / 'profiles.json'

def _load_index() -> dict:
    p = _index_path()
    if not p.exists():
        return {"active": "", "profiles": []}
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"active": "", "profiles": []}

def _save_index(index: dict) -> None:
    with open(_index_path(), 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

def _profile_path(profile_id: str) -> Path:
    return _profiles_dir() / f"{profile_id}.json"

def _slugify(name: str) -> str:
    name = str(name).strip().lower()
    name = re.sub(r'[\s_]+', '_', name)
    name = re.sub(r'[^\w\-]', '', name)
    if not name:
        name = "profile"
    return name

def list_profiles() -> dict:
    return _load_index()

def get_profile(profile_id: str) -> dict:
    p = _profile_path(profile_id)
    if not p.exists():
        raise FileNotFoundError(f"Profile not found: {profile_id}")
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_profile(name: str, data: dict | None = None) -> dict:
    index = _load_index()
    base_id = _slugify(name)
    profile_id = base_id
    counter = 1
    
    existing_ids = [p['id'] for p in index.get('profiles', [])]
    while profile_id in existing_ids:
        profile_id = f"{base_id}_{counter}"
        counter += 1
        
    profile_data = copy.deepcopy(DEFAULT_PROFILE)
    profile_data['id'] = profile_id
    profile_data['name'] = name
    profile_data['created'] = datetime.now().isoformat()
    
    def deep_merge(target: dict, source: dict):
        for k, v in source.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                deep_merge(target[k], v)
            else:
                target[k] = copy.deepcopy(v)

    if data:
        deep_merge(profile_data, data)
        
    profile_data['id'] = profile_id
    profile_data['name'] = name
    
    with open(_profile_path(profile_id), 'w', encoding='utf-8') as f:
        json.dump(profile_data, f, indent=2, ensure_ascii=False)
        
    index.setdefault('profiles', []).append({
        'id': profile_id,
        'name': name,
        'created': profile_data['created']
    })
    
    if not index.get('active'):
        index['active'] = profile_id
        
    _save_index(index)
    return profile_data

def update_profile(profile_id: str, data: dict) -> dict:
    profile_data = get_profile(profile_id)
    
    def deep_merge(target: dict, source: dict):
        for k, v in source.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                deep_merge(target[k], v)
            else:
                target[k] = copy.deepcopy(v)
                
    deep_merge(profile_data, data)
    profile_data['id'] = profile_id
    
    if 'name' in data and data['name'] != profile_data.get('name'):
        index = _load_index()
        for p in index.get('profiles', []):
            if p['id'] == profile_id:
                p['name'] = data['name']
                break
        _save_index(index)
        
    with open(_profile_path(profile_id), 'w', encoding='utf-8') as f:
        json.dump(profile_data, f, indent=2, ensure_ascii=False)
        
    return profile_data

def delete_profile(profile_id: str) -> None:
    p = _profile_path(profile_id)
    if not p.exists():
        raise FileNotFoundError(f"Profile not found: {profile_id}")
    
    p.unlink()
    
    index = _load_index()
    index['profiles'] = [prof for prof in index.get('profiles', []) if prof['id'] != profile_id]
    
    if index.get('active') == profile_id:
        if index['profiles']:
            index['active'] = index['profiles'][0]['id']
        else:
            index['active'] = ""
            
    _save_index(index)

def activate_profile(profile_id: str) -> None:
    p = _profile_path(profile_id)
    if not p.exists():
        raise FileNotFoundError(f"Profile not found: {profile_id}")
        
    index = _load_index()
    index['active'] = profile_id
    _save_index(index)

def get_active_profile() -> dict | None:
    index = _load_index()
    active_id = index.get('active')
    if not active_id:
        return None
    try:
        return get_profile(active_id)
    except FileNotFoundError:
        return None

def create_default_profile_from_config() -> dict:
    data = copy.deepcopy(DEFAULT_PROFILE)
    
    def safe_get(module_name: str, attr_name: str, default_val: any = None):
        try:
            mod = importlib.import_module(f"config.{module_name}")
            return getattr(mod, attr_name, default_val)
        except Exception:
            return default_val
            
    for k in ["first_name", "middle_name", "last_name", "phone_number", "current_city", "street", "state", "zipcode", "country", "ethnicity", "gender", "disability_status", "veteran_status"]:
        data["identity"][k] = safe_get("personals", k, data["identity"].get(k, ""))
        
    username = safe_get("secrets", "username", "")
    password = safe_get("secrets", "password", "")
    data["credentials"]["linkedin_email"] = username
    data["credentials"]["naukri_email"] = username
    data["credentials"]["linkedin_password"] = password
    data["credentials"]["naukri_password"] = password
    
    for k in ["years_of_experience", "current_ctc", "desired_salary", "notice_period", "recent_employer", "linkedIn", "website", "default_resume_path", "linkedin_headline", "linkedin_summary", "cover_letter", "user_information_all", "confidence_level"]:
        data["professional"][k] = safe_get("questions", k, data["professional"].get(k, ""))
        
    for k in ["require_visa", "us_citizenship", "pause_before_submit", "pause_at_failed_question", "overwrite_previous_answers"]:
        data["qa"][k] = safe_get("questions", k, data["qa"].get(k, ""))
        
    for k in ["willing_to_relocate", "default_yes_no_answer", "pause_at_unknown_naukri_question", "custom_naukri_answers"]:
        data["qa"][k] = safe_get("naukri_questions", k, data["qa"].get(k, ""))
        
    return create_profile("Default", data)
