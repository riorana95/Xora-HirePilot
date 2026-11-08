/* Develop by Rana Rahul — HirePilot dashboard */
let configData = {};
let selectedPlatform = 'naukri'; // sidebar platform selector for bot start
let currentProfileId = '';
let profilesIndex = { active: '', profiles: [] };

// History state
let historyView = 'applied';
let historyData = { applied: [], failed: [], skipped: [] };
let historyLimit = 50;

const tagFields = {
    search_terms: 'search_terms_tags',
    companies: 'companies_tags',
    about_company_bad_words: 'about_company_bad_words_tags',
    bad_words: 'bad_words_tags',
};

const naukriTagFields = {
    search_terms: 'naukri_search_terms_tags',
    search_locations: 'search_locations_tags',
    about_company_bad_words: 'naukri_bad_company_tags',
    bad_title_words: 'naukri_bad_title_tags',
    bad_words: 'naukri_bad_words_tags',
    filter_locations: 'naukri_filter_locations_tags',
    departments: 'naukri_departments_tags',
    salary_ranges: 'naukri_salary_ranges_tags',
    company_types: 'naukri_company_types_tags',
    role_categories: 'naukri_role_categories_tags',
    educations: 'naukri_educations_tags',
    posted_by: 'naukri_posted_by_tags',
    industries: 'naukri_industries_tags',
    top_companies: 'naukri_top_companies_tags',
    avoid_companies: 'naukri_avoid_companies_tags',
    required_skills: 'naukri_required_skills_tags',
    possessed_skills: 'naukri_possessed_skills_tags',
};

const boolFields = new Set([
    'randomize_search_order', 'easy_apply_only', 'under_10_applicants', 'in_your_network', 'fair_chance_employer',
    'pause_after_filters', 'did_masters', 'security_clearance',
    'apply_on_naukri_only', 'run_non_stop',
    'close_tabs', 'follow_companies', 'alternate_sortby', 'cycle_date_posted', 'stop_date_cycle_at_24hr',
    'run_in_background', 'safe_mode', 'stealth_mode', 'keep_screen_awake', 'smooth_scroll', 'disable_extensions', 'showAiErrorAlerts',
    'use_AI', 'stream_output'
]);

const naukriFieldIds = {
    randomize_search_order: 'naukri_randomize_search_order',
    pause_after_filters: 'naukri_pause_after_filters',
    run_non_stop: 'naukri_run_non_stop',
    current_experience: 'naukri_current_experience',
    did_masters: 'naukri_did_masters',
};

const sectionFields = {
    search: [
        'search_terms', 'search_location', 'switch_number', 'randomize_search_order',
        'sort_by', 'date_posted', 'salary', 'easy_apply_only',
        'experience_level', 'job_type', 'on_site', 'companies',
        'under_10_applicants', 'in_your_network', 'fair_chance_employer', 'pause_after_filters',
        'about_company_bad_words', 'bad_words', 'security_clearance', 'did_masters', 'current_experience',
    ],
    search_naukri: [
        'search_terms', 'search_locations', 'randomize_search_order', 'max_applications_per_search',
        'experience_min', 'experience_max', 'salary_min_lpa', 'salary_max_lpa',
        'work_mode', 'job_age_days', 'apply_on_naukri_only', 'pause_after_filters', 'run_non_stop',
        'freshness', 'filter_locations', 'departments', 'salary_ranges', 'company_types', 'role_categories',
        'educations', 'posted_by', 'industries', 'top_companies',
        'about_company_bad_words', 'bad_title_words', 'bad_words', 'avoid_companies', 'security_clearance', 'did_masters', 'current_experience',
        'required_skills', 'possessed_skills',
    ],
    settings: [
        'close_tabs', 'follow_companies', 'run_non_stop', 'alternate_sortby',
        'cycle_date_posted', 'stop_date_cycle_at_24hr', 'click_gap',
        'run_in_background', 'safe_mode', 'stealth_mode', 'keep_screen_awake',
        'smooth_scroll', 'disable_extensions', 'showAiErrorAlerts',
    ],
    secrets: ['use_AI', 'ai_provider', 'llm_api_url', 'llm_api_key', 'llm_model', 'stream_output'],
};

const multiSelectFields = ['experience_level', 'job_type', 'on_site', 'work_mode'];

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => { toast.className = 'toast'; }, 3200);
}

function escapeHtml(text) {
    if (typeof text !== 'string') return '';
    return text.replace(/[&<>'"]/g, tag => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[tag] || tag));
}

function timeAgo(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const secs = Math.floor((Date.now() - d.getTime()) / 1000);
    if (secs < 60) return 'just now';
    if (secs < 3600) return Math.floor(secs / 60) + 'm ago';
    if (secs < 86400) return Math.floor(secs / 3600) + 'h ago';
    return Math.floor(secs / 86400) + 'd ago';
}

function fmtDate(iso) {
    if (!iso) return '-';
    const d = new Date(iso);
    if (isNaN(d)) return String(iso);
    return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

/* ═══════════ Navigation ═══════════ */
const PAGE_TITLES = {
    overview: 'Overview', history: 'Job History', questions: 'AI Answers',
    unknown: 'Unknown Questions', profiles: 'Profiles', filters: 'Job Filters', config: 'Bot Config',
};

function goToPage(page) {
    document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.page === page));
    document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === 'page-' + page));
    document.getElementById('pageTitle').textContent = PAGE_TITLES[page] || page;
    document.getElementById('sidebar').classList.remove('open');
    if (page === 'overview') { loadStats(); loadTimeline(); }
    if (page === 'history') loadAllHistory();
    if (page === 'questions') loadAiAnswers();
    if (page === 'unknown') loadUnknownQuestions();
}

document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => goToPage(btn.dataset.page));
});

document.getElementById('sidebarToggle').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('open');
});

/* ═══════════ Tag inputs ═══════════ */
function createTagInput(containerId, fieldName, values = []) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '';
    const tagsWrapper = document.createElement('div');
    tagsWrapper.className = 'tags-wrapper';

    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = `Add ${fieldName.replace(/_/g, ' ')}... (Enter)`;

    let currentTags = Array.isArray(values) ? [...values] : [];

    function renderTags() {
        tagsWrapper.innerHTML = '';
        currentTags.forEach((tag, index) => {
            const tagEl = document.createElement('span');
            tagEl.className = 'tag';
            tagEl.innerHTML = `${escapeHtml(tag)} <span class="tag-remove" data-index="${index}">&times;</span>`;
            tagsWrapper.appendChild(tagEl);
        });
        tagsWrapper.appendChild(input);

        tagsWrapper.querySelectorAll('.tag-remove').forEach(btn => {
            btn.onclick = (e) => {
                const idx = parseInt(e.target.dataset.index);
                currentTags.splice(idx, 1);
                renderTags();
            };
        });
    }

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const val = input.value.trim();
            if (val && !currentTags.includes(val)) {
                currentTags.push(val);
                input.value = '';
                renderTags();
            }
        } else if (e.key === 'Backspace' && !input.value && currentTags.length > 0) {
            currentTags.pop();
            renderTags();
        }
    });

    container.appendChild(tagsWrapper);
    renderTags();

    container.getTags = () => currentTags;
}

function getTagValues(containerId) {
    const container = document.getElementById(containerId);
    return container && container.getTags ? container.getTags() : [];
}

function populateSelect(id, options, value) {
    const el = document.getElementById(id);
    if (!el || !options) return;
    el.innerHTML = options.map(opt => `<option value="${escapeHtml(String(opt))}">${escapeHtml(String(opt))}</option>`).join('');
    if (value !== undefined) el.value = String(value);
}

function populateCheckboxes(id, options, selected = []) {
    const el = document.getElementById(`${id}_checkboxes`);
    if (!el || !options) return;
    el.innerHTML = options.map(opt => `
        <label class="checkbox-label">
            <input type="checkbox" value="${escapeHtml(String(opt))}" ${selected.includes(opt) ? 'checked' : ''}>
            ${escapeHtml(String(opt))}
        </label>
    `).join('');
}

function getCheckboxValues(id) {
    const el = document.getElementById(`${id}_checkboxes`);
    if (!el) return [];
    return Array.from(el.querySelectorAll('input:checked')).map(cb => cb.value);
}

function naukriDomId(field) {
    return naukriFieldIds[field] || field;
}

function setFieldValue(id, value) {
    const el = document.getElementById(id);
    if (!el) return;

    if (el.tagName === 'SELECT') {
        el.value = typeof value === 'boolean' ? String(value) : value;
    } else if (el.type === 'checkbox') {
        el.checked = !!value;
    } else if (el.type !== 'password') {
        el.value = (value === null || value === undefined) ? '' : String(value);
    }
}

function getFieldValue(id) {
    const el = document.getElementById(id);
    if (!el) return '';

    if (el.tagName === 'SELECT') {
        if (el.value === 'true') return true;
        if (el.value === 'false') return false;
        return el.value;
    }
    if (el.type === 'checkbox') return el.checked;
    if (el.type === 'number') return el.value === '' ? null : Number(el.value);
    return el.value;
}

/* ═══════════ Profiles ═══════════ */
async function loadProfiles() {
    try {
        const res = await fetch('/api/profiles');
        const data = await res.json();
        profilesIndex = data;
        currentProfileId = data.active;

        const sel = document.getElementById('profileSelect');
        sel.innerHTML = data.profiles.map(p => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join('');
        sel.value = currentProfileId;

        if (currentProfileId) {
            await loadProfile(currentProfileId);
        }
    } catch (err) {
        showToast('Error loading profiles', 'error');
    }
}

async function loadProfile(profileId) {
    try {
        const res = await fetch(`/api/profiles/${profileId}`);
        if (!res.ok) throw new Error('Failed to load');
        const profile = await res.json();

        ['first_name', 'middle_name', 'last_name', 'phone_number', 'current_city',
         'street', 'state', 'zipcode', 'country', 'gender', 'ethnicity',
         'disability_status', 'veteran_status'].forEach(f => {
            setFieldValue(f, profile.identity?.[f] || '');
        });

        setFieldValue('prof_linkedin_email', profile.credentials?.linkedin_email || '');
        setFieldValue('prof_naukri_email', profile.credentials?.naukri_email || '');
        document.getElementById('prof_linkedin_password').value = '';
        document.getElementById('prof_naukri_password').value = '';

        ['years_of_experience', 'current_ctc', 'desired_salary', 'notice_period',
         'recent_employer', 'linkedIn', 'website', 'default_resume_path',
         'linkedin_headline', 'linkedin_summary', 'cover_letter',
         'user_information_all', 'confidence_level'].forEach(f => {
            setFieldValue(f, profile.professional?.[f] || '');
        });

        ['require_visa', 'us_citizenship', 'willing_to_relocate', 'default_yes_no_answer',
         'pause_at_unknown_naukri_question', 'pause_before_submit',
         'pause_at_failed_question', 'overwrite_previous_answers'].forEach(f => {
            setFieldValue(f, profile.qa?.[f] !== undefined ? profile.qa[f] : '');
        });

        const qaAnswers = profile.qa?.custom_naukri_answers || {};
        const qaStr = Object.entries(qaAnswers).map(([k, v]) => `${k}: ${v}`).join('\n');
        document.getElementById('custom_naukri_answers').value = qaStr;

    } catch (err) {
        showToast('Error loading profile', 'error');
    }
}

function collectProfileData() {
    const data = { identity: {}, credentials: {}, professional: {}, qa: {} };

    ['first_name', 'middle_name', 'last_name', 'phone_number', 'current_city',
     'street', 'state', 'zipcode', 'country', 'gender', 'ethnicity',
     'disability_status', 'veteran_status'].forEach(f => {
        data.identity[f] = getFieldValue(f);
    });

    data.credentials.linkedin_email = getFieldValue('prof_linkedin_email');
    data.credentials.naukri_email = getFieldValue('prof_naukri_email');
    const lPw = document.getElementById('prof_linkedin_password').value;
    const nPw = document.getElementById('prof_naukri_password').value;
    if (lPw) data.credentials.linkedin_password = lPw;
    if (nPw) data.credentials.naukri_password = nPw;

    ['years_of_experience', 'current_ctc', 'desired_salary', 'notice_period',
     'recent_employer', 'linkedIn', 'website', 'default_resume_path',
     'linkedin_headline', 'linkedin_summary', 'cover_letter',
     'user_information_all', 'confidence_level'].forEach(f => {
        data.professional[f] = getFieldValue(f);
    });

    ['require_visa', 'us_citizenship', 'willing_to_relocate', 'default_yes_no_answer',
     'pause_at_unknown_naukri_question', 'pause_before_submit',
     'pause_at_failed_question', 'overwrite_previous_answers'].forEach(f => {
        data.qa[f] = getFieldValue(f);
    });

    const qaStr = document.getElementById('custom_naukri_answers').value;
    const customAns = {};
    qaStr.split('\n').forEach(line => {
        const parts = line.split(':');
        if (parts.length >= 2) {
            const k = parts.shift().trim();
            customAns[k] = parts.join(':').trim();
        }
    });
    data.qa.custom_naukri_answers = customAns;

    return data;
}

async function saveCurrentProfile() {
    if (!currentProfileId) return;
    const data = collectProfileData();
    try {
        const res = await fetch(`/api/profiles/${currentProfileId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) throw new Error('Save failed');
        showToast('Profile saved successfully');
    } catch (err) {
        showToast('Error saving profile', 'error');
    }
}

async function createNewProfile() {
    const name = prompt('Enter profile name:');
    if (!name) return;
    try {
        const res = await fetch('/api/profiles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, data: null })
        });
        if (res.ok) {
            showToast('Profile created');
            await loadProfiles();
        }
    } catch (err) {
        showToast('Error creating profile', 'error');
    }
}

async function duplicateProfile() {
    const name = prompt('Enter name for the copy:');
    if (!name) return;
    const data = collectProfileData();
    try {
        const res = await fetch('/api/profiles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, data })
        });
        if (res.ok) {
            showToast('Profile duplicated');
            await loadProfiles();
        }
    } catch (err) {
        showToast('Error duplicating profile', 'error');
    }
}

async function deleteCurrentProfile() {
    if (!confirm('Delete this profile?')) return;
    try {
        const res = await fetch(`/api/profiles/${currentProfileId}`, { method: 'DELETE' });
        if (res.ok) {
            showToast('Profile deleted');
            await loadProfiles();
        }
    } catch (err) {
        showToast('Error deleting profile', 'error');
    }
}

document.getElementById('profileSelect').addEventListener('change', async (e) => {
    const newId = e.target.value;
    if (newId === currentProfileId) return;
    try {
        await fetch(`/api/profiles/${newId}/activate`, { method: 'POST' });
        currentProfileId = newId;
        await loadProfile(newId);
        showToast('Profile switched!');
    } catch (err) {
        showToast('Error switching profile', 'error');
    }
});

/* ═══════════ Filters / config forms ═══════════ */
function switchFilterPlatform(platform) {
    document.getElementById('linkedin-filters').style.display = platform === 'linkedin' ? 'block' : 'none';
    document.getElementById('naukri-filters').style.display = platform === 'naukri' ? 'block' : 'none';
    document.querySelectorAll('.platform-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.platform === platform);
    });
}

function collectSection(section) {
    const data = {};
    const fields = sectionFields[section];
    if (!fields) return data;

    fields.forEach(f => {
        let val;
        let idToUse = section === 'search_naukri' ? naukriDomId(f) : f;

        if (tagFields[f] && section === 'search') {
            val = getTagValues(tagFields[f]);
        } else if (naukriTagFields[f] && section === 'search_naukri') {
            val = getTagValues(naukriTagFields[f]);
        } else if (multiSelectFields.includes(f)) {
            val = getCheckboxValues(f);
        } else {
            val = getFieldValue(idToUse);
            if (boolFields.has(f)) {
                val = val === true || val === 'true';
            } else if (typeof val === 'string' && val.trim() !== '') {
                if (!isNaN(val) && f !== 'llm_api_key' && f !== 'llm_api_url') val = Number(val);
            }
        }

        if (f === 'llm_api_key' && !val) {
            // retain existing key if left blank
        } else if (val === null || val === undefined) {
            // blank numeric field: keep the existing config value
        } else {
            data[f] = val;
        }
    });
    return data;
}

async function saveSection(sectionName) {
    const data = collectSection(sectionName);
    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sections: { [sectionName]: data } })
        });

        if (response.ok) {
            showToast(`${sectionName.replace('_', ' ')} saved successfully`);
        } else {
            showToast('Failed to save settings', 'error');
        }
    } catch (error) {
        console.error('Error saving:', error);
        showToast('Error saving settings', 'error');
    }
}

async function saveBotConfig() {
    const sections = {
        settings: collectSection('settings'),
        secrets: collectSection('secrets'),
    };
    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sections })
        });

        if (response.ok) {
            showToast('Bot config saved successfully');
        } else {
            showToast('Failed to save bot config', 'error');
        }
    } catch (error) {
        showToast('Error saving bot config', 'error');
    }
}

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        configData = await response.json();

        const options = configData.options || {};

        populateSelect('gender', options.gender || []);
        populateSelect('ethnicity', options.ethnicity || []);
        populateSelect('disability_status', options.disability_status || []);
        populateSelect('veteran_status', options.veteran_status || []);
        populateSelect('require_visa', options.require_visa || []);
        populateSelect('us_citizenship', options.us_citizenship || []);

        populateSelect('sort_by', options.sort_by || []);
        populateSelect('date_posted', options.date_posted || []);
        populateSelect('salary', options.salary || []);
        populateSelect('freshness', options.date_posted || []);
        populateSelect('ai_provider', options.ai_provider || []);

        populateCheckboxes('experience_level', options.experience_level || [], configData.sections?.search?.experience_level || []);
        populateCheckboxes('job_type', options.job_type || [], configData.sections?.search?.job_type || []);
        populateCheckboxes('on_site', options.on_site || [], configData.sections?.search?.on_site || []);
        populateCheckboxes('work_mode', options.work_mode || [], configData.sections?.search_naukri?.work_mode || []);

        const sections = configData.sections || {};

        ['search', 'search_naukri', 'settings', 'secrets'].forEach(sec => {
            const data = sections[sec] || {};
            sectionFields[sec].forEach(f => {
                let idToUse = sec === 'search_naukri' ? naukriDomId(f) : f;

                if (tagFields[f] && sec === 'search') {
                    createTagInput(tagFields[f], f, data[f] || []);
                } else if (naukriTagFields[f] && sec === 'search_naukri') {
                    createTagInput(naukriTagFields[f], f, data[f] || []);
                } else if (!multiSelectFields.includes(f)) {
                    if (f !== 'llm_api_key') {
                        setFieldValue(idToUse, data[f]);
                    }
                }
            });
        });

    } catch (error) {
        console.error('Error loading config:', error);
        showToast('Error loading configuration', 'error');
    }
}

/* ═══════════ Bot control ═══════════ */
async function updateBotStatus() {
    try {
        const response = await fetch('/api/bot/status');
        const data = await response.json();

        const dot = document.getElementById('statusDot');
        const text = document.getElementById('statusText');
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const platformSelect = document.getElementById('platformSelect');

        if (data.running) {
            dot.className = 'status-dot running';
            text.textContent = `Running (${data.platform})`;
            startBtn.disabled = true;
            stopBtn.disabled = false;
            platformSelect.disabled = true;
            if (data.platform) platformSelect.value = data.platform;
        } else {
            dot.className = 'status-dot stopped';
            text.textContent = 'Stopped';
            startBtn.disabled = false;
            stopBtn.disabled = true;
            platformSelect.disabled = false;
        }
        loadBotLogs();
    } catch (error) {
        console.error('Error fetching bot status:', error);
    }
}

async function startBot() {
    const platform = document.getElementById('platformSelect').value;
    const startBtn = document.getElementById('startBtn');
    try {
        if (startBtn) { startBtn.disabled = true; startBtn.textContent = 'Starting...'; }
        goToPage('overview');

        // Preflight: config/import errors surface here instead of a silent no-op.
        try {
            const pre = await fetch('/api/bot/preflight', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ platform })
            });
            const preData = await pre.json();
            if (!preData.ok) {
                showToast('Bot config check failed — see console output', 'error');
                await updateBotStatus();
                return;
            }
        } catch (e) { /* preflight is best-effort; continue to start */ }

        const response = await fetch('/api/bot/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform })
        });

        if (response.ok) {
            showToast(`Started ${platform} bot`);
            updateBotStatus();
        } else {
            const data = await response.json();
            showToast(data.error || 'Failed to start bot', 'error');
            await updateBotStatus();
        }
    } catch (error) {
        showToast('Error starting bot', 'error');
    } finally {
        if (startBtn) { startBtn.disabled = false; startBtn.textContent = '▶ Start Bot'; }
    }
}

async function stopBot() {
    try {
        const response = await fetch('/api/bot/stop', { method: 'POST' });
        if (response.ok) {
            showToast('Stopping bot...');
            setTimeout(updateBotStatus, 1000);
        } else {
            showToast('Failed to stop bot', 'error');
        }
    } catch (error) {
        showToast('Error stopping bot', 'error');
    }
}

/* ═══════════ Stats + timeline (Overview) ═══════════ */
async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const s = await res.json();
        document.getElementById('statApplied').textContent = s.applied || 0;
        document.getElementById('statAppliedToday').textContent = `${s.applied_today || 0} today`;
        document.getElementById('statFailed').textContent = s.failed || 0;
        document.getElementById('statFailedToday').textContent = `${s.failed_today || 0} today`;
        document.getElementById('statSkipped').textContent = s.skipped || 0;
        document.getElementById('statSkippedToday').textContent = `${s.skipped_today || 0} today`;
        document.getElementById('statAiPending').textContent = s.ai_pending_review || 0;

        const aiBadge = document.getElementById('navAiBadge');
        if (s.ai_pending_review > 0) { aiBadge.style.display = ''; aiBadge.textContent = s.ai_pending_review; }
        else aiBadge.style.display = 'none';
        const uqBadge = document.getElementById('navUnknownBadge');
        if (s.unknown_questions > 0) { uqBadge.style.display = ''; uqBadge.textContent = s.unknown_questions; }
        else uqBadge.style.display = 'none';
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadTimeline() {
    try {
        const res = await fetch('/api/jobs/timeline');
        const data = await res.json();
        const el = document.getElementById('miniTimeline');
        const events = data.events || [];
        if (!events.length) return; // keep default empty-state
        el.innerHTML = events.slice(0, 40).map(e => {
            const cls = e.action === 'APPLIED' ? 'applied' : (e.action === 'FAILED' ? 'failed' : 'skipped');
            const reason = e.action === 'SKIPPED'
                ? `<div class="tl-reason">why: <b>${escapeHtml(e.error || '')}</b></div>`
                : (e.error ? `<div class="tl-reason">${escapeHtml(e.error)}</div>` : '');
            const nq = (e.questions_answered || []).length;
            const qnote = nq ? `<div class="tl-reason">${nq} question${nq > 1 ? 's' : ''} answered</div>` : '';
            return `
                <div class="tl-item">
                    <span class="tl-dot ${cls}"></span>
                    <div class="tl-body">
                        <div class="tl-title">"${escapeHtml(e.title || '(untitled)')}" <span class="company">| ${escapeHtml(e.company || '')}</span></div>
                        ${reason}${qnote}
                        <span class="tl-time">${timeAgo(e.time)}</span>
                        ${e.job_id ? ` <a class="tl-link" onclick="openJobDrawer('${escapeHtml(e.job_id)}', '${escapeHtml(e.title || '')}')">details</a>` : ''}
                    </div>
                </div>`;
        }).join('');
    } catch (error) {
        console.error('Error loading timeline:', error);
    }
}

/* ═══════════ Job History ═══════════ */
document.querySelectorAll('.seg-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        historyView = btn.dataset.view;
        document.querySelectorAll('.seg-btn').forEach(b => b.classList.toggle('active', b === btn));
        renderHistory();
    });
});

async function loadAllHistory() {
    await Promise.all([loadAppliedJobs(), loadFailedJobs(), loadSkippedJobs(), loadHistoryCounts()]);
    renderHistory();
}

async function loadAppliedJobs() {
    try {
        const response = await fetch('/applied-jobs');
        const jobs = await response.json();
        historyData.applied = Array.isArray(jobs) ? jobs : [];
    } catch (error) {
        console.error('Error loading applied jobs:', error);
        historyData.applied = [];
    }
}

async function loadFailedJobs() {
    try {
        const response = await fetch('/api/jobs/failed');
        const jobs = await response.json();
        historyData.failed = Array.isArray(jobs) ? jobs : [];
    } catch (error) {
        console.error('Error loading failed jobs:', error);
        historyData.failed = [];
    }
}

async function loadSkippedJobs() {
    try {
        const response = await fetch('/api/jobs/skipped');
        const jobs = await response.json();
        historyData.skipped = Array.isArray(jobs) ? jobs : [];
    } catch (error) {
        console.error('Error loading skipped jobs:', error);
        historyData.skipped = [];
    }
}

async function loadHistoryCounts() {
    try {
        const res = await fetch('/api/jobs/summary');
        const c = await res.json();
        document.getElementById('segApplied').textContent = c.applied || 0;
        document.getElementById('segFailed').textContent = c.failed || 0;
        document.getElementById('segSkipped').textContent = c.skipped || 0;
        const badge = document.getElementById('navHistoryBadge');
        if ((c.applied || 0) > 0) { badge.style.display = ''; badge.textContent = c.applied; }
        else badge.style.display = 'none';
    } catch (error) {
        console.error('Error loading history counts:', error);
    }
}

function historyMatches(job) {
    const platformFilter = document.getElementById('historyPlatformFilter').value;
    const q = (document.getElementById('historySearch').value || '').toLowerCase();
    if (platformFilter && (job.Platform || '').toLowerCase() !== platformFilter.toLowerCase()) return false;
    if (q) {
        const hay = `${job.Title || ''} ${job.Company || ''} ${job.Reason || ''} ${job.Detail || ''} ${job.Location || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
    }
    return true;
}

function renderHistory() {
    document.getElementById('appliedTableWrap').style.display = historyView === 'applied' ? '' : 'none';
    document.getElementById('failedTableWrap').style.display = historyView === 'failed' ? '' : 'none';
    document.getElementById('skippedTableWrap').style.display = historyView === 'skipped' ? '' : 'none';

    const tbody = { applied: 'jobsBody', failed: 'failedJobsBody', skipped: 'skippedJobsBody' }[historyView];
    const el = document.getElementById(tbody);
    const empty = document.getElementById('historyEmpty');
    const moreWrap = document.getElementById('loadMoreWrap');

    const rows = historyData[historyView].filter(historyMatches);
    const shown = rows.slice(0, historyLimit);

    if (!shown.length) {
        el.innerHTML = '';
        empty.style.display = 'block';
        const msgs = {
            applied: 'No applied jobs match. Start the bot to begin applying!',
            failed: 'No failed applications match. 🎉',
            skipped: 'No skipped jobs match.',
        };
        empty.textContent = msgs[historyView];
        moreWrap.style.display = 'none';
        return;
    }
    empty.style.display = 'none';
    moreWrap.style.display = rows.length > historyLimit ? '' : 'none';

    if (historyView === 'applied') {
        el.innerHTML = shown.map((job, i) => appliedRow(job, i)).join('');
    } else if (historyView === 'failed') {
        el.innerHTML = shown.map((job, i) => failedRow(job, i)).join('');
    } else {
        el.innerHTML = shown.map((job, i) => skippedRow(job, i)).join('');
    }
}

function loadMoreHistory() {
    historyLimit += 100;
    renderHistory();
}

function expiredHint(job) {
    // Naukri job pages expire (~30 days). Rather than a dead link, offer the
    // fallback search so the row stays actionable.
    const plat = (job.Platform || '').toLowerCase();
    if (plat !== 'naukri' || !job.Job_Link) return '';
    return `
        <div class="job-sub">
            <a href="${escapeHtml(job.Job_Link)}" target="_blank" class="btn btn-outline btn-sm">Open job</a>
        </div>
        <div class="expired-hint" title="Naukri removes job pages ~30 days after posting">
            ⚠ link may be expired —
            <a href="${escapeHtml(job.Search_Link || '#')}" target="_blank">find similar live jobs</a>
        </div>`;
}

function appliedRow(job, index) {
    const date = (job.Date_Applied && job.Date_Applied !== 'Pending') ? job.Date_Applied : 'pending';
    const plat = job.Platform || 'LinkedIn';
    const platClass = plat.toLowerCase() === 'naukri' ? 'plat-naukri' : 'plat-linkedin';
    return `
        <tr>
            <td>${index + 1}</td>
            <td class="job-title-cell">
                <div>${escapeHtml(job.Title || '')}</div>
                ${job.Job_ID ? `<div class="job-sub"><a class="tl-link" onclick="openJobDrawer('${escapeHtml(job.Job_ID)}', '${escapeHtml(job.Title || '')}')">full history</a></div>` : ''}
            </td>
            <td>${escapeHtml(job.Company || '')}</td>
            <td>${escapeHtml(job.Location || '-')}</td>
            <td>${escapeHtml(date)}</td>
            <td>
                <span class="platform-badge ${platClass}">${plat}</span>
                ${expiredHint(job)}
            </td>
        </tr>
    `;
}

function reasonPillClass(reason) {
    const r = (reason || '').toLowerCase();
    if (r.includes('skill')) return 'skill';
    if (r.includes('experience') || r.includes('exp')) return 'exp';
    return 'fail';
}

function failedRow(job, index) {
    return `
        <tr>
            <td>${index + 1}</td>
            <td class="job-title-cell">
                <div>${escapeHtml(job.Title || job.Job_ID || '')}</div>
                ${job.Job_ID ? `<div class="job-sub"><a class="tl-link" onclick="openJobDrawer('${escapeHtml(job.Job_ID)}', '${escapeHtml(job.Title || '')}')">full history</a></div>` : ''}
            </td>
            <td>${escapeHtml(job.Company || '')}</td>
            <td>
                <span class="reason-pill ${reasonPillClass(job.Reason)}">${escapeHtml(job.Reason || 'Unknown')}</span>
                ${job.Detail ? `<div class="detail-text">${escapeHtml(job.Detail.slice(0, 140))}</div>` : ''}
            </td>
            <td>${escapeHtml(job.Date_Tried || '-')}</td>
            <td>${job.Job_Link ? `<a href="${escapeHtml(job.Job_Link)}" target="_blank" class="btn btn-outline btn-sm">Open</a>` : '-'}</td>
        </tr>
    `;
}

function skippedRow(job, index) {
    const detail = job.Detail || '';
    return `
        <tr>
            <td>${index + 1}</td>
            <td class="job-title-cell">
                <div>${escapeHtml(job.Title || '')}</div>
                ${job.Job_ID ? `<div class="job-sub"><a class="tl-link" onclick="openJobDrawer('${escapeHtml(job.Job_ID)}', '${escapeHtml(job.Title || '')}')">full history</a></div>` : ''}
            </td>
            <td>${escapeHtml(job.Company || '')}</td>
            <td>
                <span class="reason-pill ${reasonPillClass(job.Reason)}">${escapeHtml(job.Reason || 'Unknown')}</span>
                ${detail ? `<div class="detail-text">${escapeHtml(detail.slice(0, 140))}</div>` : ''}
            </td>
            <td>${escapeHtml(job.Experience || '-')}</td>
            <td>${escapeHtml(job.Date_Skipped || '-')}</td>
        </tr>
    `;
}

/* ═══════════ Job drawer ═══════════ */
async function openJobDrawer(jobId, title) {
    if (!jobId) return;
    document.getElementById('drawerTitle').textContent = title || 'Job';
    document.getElementById('drawerBody').innerHTML = '<p class="muted">Loading job history...</p>';
    document.getElementById('drawerBackdrop').classList.add('open');
    document.getElementById('jobDrawer').classList.add('open');

    try {
        const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/detail`);
        if (!res.ok) throw new Error('No history');
        const data = await res.json();

        const events = (data.events || []).slice().reverse();
        const applied = events.filter(e => e.action === 'APPLIED');
        const last = events[0] || {};

        let html = `
            <div class="drawer-sec">
                <h4>Status</h4>
                ${applied.length
                    ? `<span class="status-chip answered">✅ APPLIED ${applied.length}×</span>`
                    : `<span class="status-chip pending">not applied</span>`}
                <div class="drawer-meta" style="margin-top:10px">
                    <span>Job ID: <b>${escapeHtml(jobId.slice(0, 60))}${jobId.length > 60 ? '…' : ''}</b></span>
                    ${last.search_term ? `<span>Found via search: <b>${escapeHtml(last.search_term)}${last.search_location ? ' in ' + escapeHtml(last.search_location) : ''}</b></span>` : ''}
                </div>
            </div>`;

        const allQ = events.flatMap(e => e.questions_answered || []);
        if (allQ.length) {
            html += `
                <div class="drawer-sec">
                    <h4>Questions answered (${allQ.length})</h4>
                    ${allQ.map(qa => `
                        <div class="qa-row">
                            <div class="q">Q: ${escapeHtml(qa.q || '')}</div>
                            <div class="a">A: ${escapeHtml(qa.a || '')}</div>
                        </div>`).join('')}
                </div>`;
        }

        html += `
            <div class="drawer-sec">
                <h4>Full history (${events.length} event${events.length !== 1 ? 's' : ''}, newest first)</h4>
                ${events.map(e => `
                    <div class="qa-row">
                        <div class="q">${fmtDate(e.time)} — <b style="color:${e.action === 'APPLIED' ? '#34d399' : (e.action === 'FAILED' ? '#f87171' : '#8ea0bd')}">${escapeHtml(e.action)}</b>${e.error ? ` — ${escapeHtml(e.error)}` : ''}</div>
                    </div>`).join('')}
            </div>`;

        if (last.description_snippet) {
            html += `
                <div class="drawer-sec">
                    <h4>Job description (snippet)</h4>
                    <div class="qa-row" style="max-height:180px;overflow-y:auto">${escapeHtml(last.description_snippet)}</div>
                </div>`;
        }

        html += `
            <div class="drawer-sec">
                <h4>Links</h4>
                <a class="btn btn-outline btn-sm" href="https://www.naukri.com/${encodeURIComponent((title || 'jobs').toLowerCase().replace(/\s+/g, '-'))}-jobs" target="_blank">Find similar jobs</a>
            </div>`;

        document.getElementById('drawerBody').innerHTML = html;
    } catch (error) {
        document.getElementById('drawerBody').innerHTML =
            '<p class="muted">No detailed history recorded for this job (it may predate the detailed activity log).</p>';
    }
}

function closeDrawer() {
    document.getElementById('drawerBackdrop').classList.remove('open');
    document.getElementById('jobDrawer').classList.remove('open');
}

/* ═══════════ AI Answers review ═══════════ */
let aiAnswersCache = [];

async function loadAiAnswers() {
    try {
        const res = await fetch('/api/naukri/ai-answers');
        const data = await res.json();
        aiAnswersCache = data.answers || [];
        const c = data.counts || {};
        document.getElementById('aiCounts').innerHTML = `
            <span class="ai-count-pill pend">⏳ ${c.pending || 0} pending review</span>
            <span class="ai-count-pill ok">✅ ${c.correct || 0} correct</span>
            <span class="ai-count-pill bad">❌ ${c.wrong || 0} wrong</span>
            <span class="ai-count-pill">${c.total || 0} total</span>`;
        // Default the filter to "all" so reviewed answers stay visible.
        const sel = document.getElementById('aiFilter');
        if (sel && !sel.dataset.touched) sel.value = 'all';
        renderAiAnswers();
        loadStats(); // refresh sidebar badge
    } catch (error) {
        console.error('Error loading AI answers:', error);
    }
}

document.getElementById('aiFilter').addEventListener('change', (e) => {
    e.target.dataset.touched = '1';
    renderAiAnswers();
});
document.getElementById('aiSearch').addEventListener('input', () => renderAiAnswers());

function renderAiAnswers() {
    const listEl = document.getElementById('aiAnswersList');
    const filter = document.getElementById('aiFilter').value;
    const q = (document.getElementById('aiSearch').value || '').toLowerCase();

    let items = aiAnswersCache;
    if (filter !== 'all') items = items.filter(a => a.feedback === filter);
    if (q) items = items.filter(a => `${a.question} ${a.answer}`.toLowerCase().includes(q));

    if (!items.length) {
        listEl.innerHTML = `<div class="empty-state">${aiAnswersCache.length
            ? 'No AI answers match this filter.'
            : 'No AI answers recorded yet. They appear here after the next bot run.'}</div>`;
        return;
    }

    listEl.innerHTML = items.map(a => aiCardHtml(a)).join('');
}

function aiCardHtml(a) {
    const fb = a.feedback || 'pending';
    return `
        <div class="ai-card ${fb}">
            <div class="ai-q">${escapeHtml(a.question)}</div>
            <div class="ai-a">AI answered: "${escapeHtml(a.answer)}"</div>
            ${a.options && a.options.length ? `<div class="ai-opts">options seen: ${escapeHtml(a.options.join(' | '))}</div>` : ''}
            <div class="ai-meta">
                <span>asked ${a.count || 1}×</span>
                <span>last: ${timeAgo(a.last_time)}</span>
                <span>status: ${fb === 'correct' ? '✅ correct' : fb === 'wrong' ? '❌ wrong' : '⏳ pending review'}</span>
            </div>
            <div class="ai-actions">
                ${fb !== 'correct' ? `<button class="btn btn-sm btn-success" onclick="markAiAnswer('${escapeHtml(a.question)}', 'correct')">✓ Correct</button>` : ''}
                ${fb !== 'wrong' ? `<button class="btn btn-sm btn-danger" onclick="markAiAnswer('${escapeHtml(a.question)}', 'wrong')">✗ Wrong</button>` : ''}
                ${fb === 'wrong' && !a.keyword ? `<button class="btn btn-sm btn-outline" onclick="showTeachForm(this, '${escapeHtml(a.question)}')">🎓 Teach correct answer</button>` : ''}
            </div>
            ${a.keyword ? `<div class="ai-taught">🎓 taught pair: "${escapeHtml(a.keyword)}" — the bot now answers this itself</div>`
                        : (fb === 'wrong' ? `<div class="ai-taught">Teach a keyword:answer pair so the bot answers this itself next time.</div>` : '')}
        </div>
    `;
}

async function markAiAnswer(question, feedback) {
    try {
        const res = await fetch('/api/naukri/ai-answers/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, feedback })
        });
        if (res.ok) {
            showToast(`Marked as ${feedback}`);
            await loadAiAnswers();
        } else {
            showToast('Failed to save feedback', 'error');
        }
    } catch (error) {
        showToast('Error saving feedback', 'error');
    }
}

function showTeachForm(btn, question) {
    const card = btn.closest('.ai-card');
    const existing = card.querySelector('.teach-form');
    if (existing) { existing.remove(); return; }
    const div = document.createElement('div');
    div.className = 'teach-form ai-taught';
    div.style.display = 'block';
    div.innerHTML = `
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px">
            <input class="form-control" style="width:160px" placeholder="keyword (e.g. relocate)" id="tf-kw">
            <input class="form-control" style="width:180px" placeholder="answer (e.g. No)" id="tf-ans">
            <button class="btn btn-sm btn-primary" onclick="teachAiAnswer(this, '${escapeHtml(question)}')">Save pair</button>
        </div>
        <div class="help-text" style="margin-top:4px">The keyword must appear inside the question; the answer is used verbatim.</div>`;
    card.appendChild(div);
}

async function teachAiAnswer(btn, question) {
    const card = btn.closest('.ai-card');
    const keyword = card.querySelector('#tf-kw').value.trim();
    const answer = card.querySelector('#tf-ans').value.trim();
    if (!keyword || !answer) {
        showToast('Both keyword and answer are required', 'error');
        return;
    }
    try {
        const res = await fetch('/api/naukri/ai-answers/teach', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, keyword, answer })
        });
        if (res.ok) {
            showToast(`Taught: "${keyword}" → "${answer}"`);
            await loadAiAnswers();
            await loadProfile(currentProfileId); // refresh the custom-answers textarea
        } else {
            showToast('Failed to teach pair', 'error');
        }
    } catch (error) {
        showToast('Error teaching pair', 'error');
    }
}

/* ═══════════ Unknown questions ═══════════ */
async function loadUnknownQuestions() {
    try {
        const res = await fetch('/api/naukri/unknown-questions');
        const data = await res.json();

        const empty = document.getElementById('unknownEmpty');
        const table = document.getElementById('unknownTableWrap');
        const bar = document.getElementById('unknownAnswerBar');
        const tbody = document.getElementById('unknownQuestionsBody');

        if (!data.questions || data.questions.length === 0) {
            empty.style.display = 'block';
            table.style.display = 'none';
            bar.style.display = 'none';
            return;
        }

        empty.style.display = 'none';
        table.style.display = 'block';
        bar.style.display = 'flex';

        tbody.innerHTML = data.questions.map((q, idx) => {
            const answered = q.status === 'answered';
            return `
            <tr class="${answered ? 'uq-row-answered' : ''}">
                <td>${idx + 1}</td>
                <td style="max-width: 300px; word-wrap: break-word;">${escapeHtml(q.question)}</td>
                <td style="max-width: 200px; word-wrap: break-word;">${q.options ? escapeHtml(q.options.join(', ')) : 'free text'}</td>
                <td>${answered
                    ? `<span class="status-chip answered">✓ Answered: ${escapeHtml(q.existing_answer || '')}</span>`
                    : '<span class="status-chip pending">pending</span>'}</td>
                <td><input type="text" class="uq-keyword form-control" placeholder="keyword" style="width: 120px;" value="${escapeHtml(q.suggested_keyword || q.matched_keyword || '')}" ${answered ? 'disabled' : ''}></td>
                <td><input type="text" class="uq-answer form-control" placeholder="your answer" style="width: 150px;" value="${escapeHtml(answered ? (q.existing_answer || '') : '')}" ${answered ? 'disabled' : ''}></td>
            </tr>`;
        }).join('');

        loadStats(); // refresh sidebar badge
    } catch (err) {
        console.error('Error loading unknown questions', err);
    }
}

async function saveUnknownAnswers() {
    const answers = {};
    document.querySelectorAll('#unknownQuestionsBody tr').forEach(tr => {
        const keywordEl = tr.querySelector('.uq-keyword');
        const answerEl = tr.querySelector('.uq-answer');
        if (!keywordEl || keywordEl.disabled) return;
        const keyword = keywordEl.value.trim();
        const answer = answerEl.value.trim();
        if (keyword && answer) {
            answers[keyword] = answer;
        }
    });

    if (Object.keys(answers).length === 0) {
        showToast('No new answers provided', 'error');
        return;
    }

    try {
        const res = await fetch('/api/naukri/answer-questions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answers })
        });

        if (res.ok) {
            const data = await res.json();
            showToast(`Saved ${Object.keys(answers).length} answer(s) — saved to profile & config`);
            await loadUnknownQuestions();  // rows flip to green immediately
            await loadProfile(currentProfileId); // refresh custom answers textarea
        } else {
            showToast('Failed to save answers', 'error');
        }
    } catch (err) {
        showToast('Error saving answers', 'error');
    }
}

/* ═══════════ Bot console ═══════════ */
async function loadBotLogs() {
    try {
        const res = await fetch('/api/bot/logs');
        const data = await res.json();
        const output = document.getElementById('consoleOutput');
        const status = document.getElementById('consoleStatus');

        if (data.lines.length > 0) {
            const html = data.lines.map(line => {
                if (/^\[(FAILED|GAVE UP)\]|error|exception|traceback/i.test(line)) {
                    return `<span class="console-error">${escapeHtml(line)}</span>`;
                }
                if (/warning/i.test(line)) {
                    return `<span class="console-warn">${escapeHtml(line)}</span>`;
                }
                if (/^\[(APPLIED|ALREADY APPLIED)|applied|success|saved/i.test(line)) {
                    return `<span class="console-success">${escapeHtml(line)}</span>`;
                }
                if (/^\[SKIPPED\]|skipped|skipping/i.test(line)) {
                    return `<span class="console-info">${escapeHtml(line)}</span>`;
                }
                return escapeHtml(line);
            }).join('\n');
            output.innerHTML = html;
            output.scrollTop = output.scrollHeight;
        }

        if (data.running) {
            status.textContent = '● Running';
            status.className = 'console-status running';
        } else if (data.exit_code !== null && data.exit_code !== undefined) {
            status.textContent = data.exit_code === 0 ? '● Stopped' : `● Error (exit ${data.exit_code})`;
            status.className = data.exit_code === 0 ? 'console-status' : 'console-status error';
        } else {
            status.textContent = '○ Idle';
            status.className = 'console-status';
        }
    } catch (_) {}
}

async function clearBotLogs() {
    await fetch('/api/bot/logs/clear', { method: 'POST' });
    document.getElementById('consoleOutput').innerHTML = 'Logs cleared.';
}

/* ═══════════ Init ═══════════ */
document.addEventListener('DOMContentLoaded', () => {
    loadProfiles();
    loadConfig();
    updateBotStatus();
    loadStats();
    loadTimeline();
    setInterval(updateBotStatus, 5000);
    setInterval(loadBotLogs, 2000);
    setInterval(() => {
        // Keep the overview fresh while the bot runs.
        if (document.getElementById('page-overview').classList.contains('active')) {
            loadTimeline();
            loadStats();
        }
    }, 15000);
});
