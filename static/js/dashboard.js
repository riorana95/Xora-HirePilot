/* Develop by Rana Rahul */

let configData = {};
let selectedPlatform = 'linkedin';

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
};

const naukriFieldIds = {
    randomize_search_order: 'naukri_randomize_search_order',
    pause_after_filters: 'naukri_pause_after_filters',
    run_non_stop: 'naukri_run_non_stop',
    current_experience: 'naukri_current_experience',
    did_masters: 'naukri_did_masters',
};

const multiSelectFields = ['experience_level', 'job_type', 'on_site', 'work_mode'];
const boolFields = new Set([
    'randomize_search_order', 'easy_apply_only', 'under_10_applicants', 'in_your_network',
    'fair_chance_employer', 'pause_after_filters', 'did_masters', 'security_clearance',
    'apply_on_naukri_only', 'naukri_run_non_stop', 'naukri_pause_after_filters',
    'pause_at_unknown_naukri_question',
    'use_AI', 'stream_output', 'close_tabs', 'follow_companies', 'run_non_stop',
    'alternate_sortby', 'cycle_date_posted', 'stop_date_cycle_at_24hr', 'run_in_background',
    'safe_mode', 'stealth_mode', 'keep_screen_awake', 'smooth_scroll', 'disable_extensions',
    'pause_before_submit', 'pause_at_failed_question', 'overwrite_previous_answers',
    'apply_on_naukri_only',
]);

/* ───── Tab Switching ───── */
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
        if (btn.dataset.tab === 'history') loadJobs();
        if (btn.dataset.tab === 'naukri-profile') loadUnknownQuestions();
    });
});

document.getElementById('platformSelect').addEventListener('change', e => {
    selectedPlatform = e.target.value;
});

/* ───── Toast ───── */
function showToast(message, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
}

/* ───── Tag Input ───── */
function createTagInput(containerId, fieldName, values = []) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    container.dataset.field = fieldName;

    function renderTags() {
        container.querySelectorAll('.tag').forEach(t => t.remove());
        const tags = JSON.parse(container.dataset.values || '[]');
        tags.forEach((tag, i) => {
            const el = document.createElement('span');
            el.className = 'tag';
            el.innerHTML = `${escapeHtml(tag)} <button type="button">&times;</button>`;
            el.querySelector('button').onclick = () => {
                tags.splice(i, 1);
                container.dataset.values = JSON.stringify(tags);
                renderTags();
            };
            container.insertBefore(el, container.querySelector('input'));
        });
    }

    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Type and press Enter...';
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter' && input.value.trim()) {
            e.preventDefault();
            const tags = JSON.parse(container.dataset.values || '[]');
            tags.push(input.value.trim());
            container.dataset.values = JSON.stringify(tags);
            input.value = '';
            renderTags();
        }
    });
    container.appendChild(input);
    container.dataset.values = JSON.stringify(values);
    renderTags();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/* ───── Form Helpers ───── */
function populateSelect(id, options, value) {
    const el = document.getElementById(id);
    if (!el || !options) return;
    el.innerHTML = options.map(o =>
        `<option value="${escapeHtml(o)}" ${o === value ? 'selected' : ''}>${o || '(None)'}</option>`
    ).join('');
}

function populateCheckboxes(id, options, selected = []) {
    const el = document.getElementById(id);
    if (!el || !options) return;
    el.innerHTML = options.map(o =>
        `<label><input type="checkbox" value="${escapeHtml(o)}" ${selected.includes(o) ? 'checked' : ''}> ${o}</label>`
    ).join('');
}

function setFieldValue(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    if (el.tagName === 'SELECT' && (boolFields.has(id) || boolFields.has(id.replace(/^naukri_/, '')))) {
        el.value = String(value).toLowerCase();
    } else if (el.tagName === 'SELECT') {
        el.value = value ?? '';
    } else if (['number', 'text', 'email', 'password'].includes(el.type)) {
        el.value = value ?? '';
    } else if (el.tagName === 'TEXTAREA') {
        el.value = value ?? '';
    }
}

function getFieldValue(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    const baseId = id.replace(/^naukri_/, '');
    if (boolFields.has(id) || boolFields.has(baseId)) return el.value === 'true';
    if (el.type === 'number') return parseInt(el.value, 10) || 0;
    return el.value;
}

function getTagValues(containerId) {
    const container = document.getElementById(containerId);
    return JSON.parse(container?.dataset.values || '[]');
}

function getCheckboxValues(id) {
    return [...document.querySelectorAll(`#${id} input:checked`)].map(cb => cb.value);
}

/* ───── Section Field Maps ───── */
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
        'about_company_bad_words', 'bad_title_words', 'bad_words', 'security_clearance', 'did_masters', 'current_experience',
    ],
    naukri_questions: [
        'willing_to_relocate', 'default_yes_no_answer', 'pause_at_unknown_naukri_question',
    ],
    personals: [
        'first_name', 'middle_name', 'last_name', 'phone_number', 'current_city',
        'street', 'state', 'zipcode', 'country', 'ethnicity', 'gender',
        'disability_status', 'veteran_status',
    ],
    questions: [
        'default_resume_path', 'years_of_experience', 'require_visa', 'website', 'linkedIn',
        'us_citizenship', 'desired_salary', 'current_ctc', 'notice_period',
        'linkedin_headline', 'linkedin_summary', 'cover_letter',
        'recent_employer', 'confidence_level',
        'pause_before_submit', 'pause_at_failed_question', 'overwrite_previous_answers',
    ],
    secrets: ['username', 'password', 'use_AI', 'ai_provider', 'llm_api_url', 'llm_api_key', 'llm_model', 'stream_output'],
    settings: [
        'close_tabs', 'follow_companies', 'run_non_stop', 'alternate_sortby',
        'cycle_date_posted', 'stop_date_cycle_at_24hr', 'click_gap',
        'run_in_background', 'safe_mode', 'stealth_mode', 'keep_screen_awake',
        'smooth_scroll', 'disable_extensions',
    ],
};

function naukriDomId(field) {
    return naukriFieldIds[field] || field;
}

/* ───── Section Collection ───── */
function collectSection(section) {
    const data = {};
    const tags = section === 'search_naukri' ? naukriTagFields : tagFields;
    for (const field of sectionFields[section]) {
        const domId = section === 'search_naukri' ? naukriDomId(field) : field;
        if (tags[field]) {
            data[field] = getTagValues(tags[field]);
        } else if (multiSelectFields.includes(field)) {
            data[field] = getCheckboxValues(field);
        } else {
            data[field] = getFieldValue(domId);
        }
    }
    return data;
}

/* ───── Save Section ───── */
async function saveSection(section) {
    try {
        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sections: { [section]: collectSection(section) } }),
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.error || 'Save failed');
        showToast('Settings saved successfully!');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

/* ───── Save Naukri Profile (credentials + personals + questions + naukri_questions) ───── */
async function saveNaukriProfile() {
    try {
        // Collect Naukri Profile tab fields and map them to config sections
        const personalUpdates = {
            first_name: document.getElementById('np_first_name')?.value || '',
            middle_name: document.getElementById('np_middle_name')?.value || '',
            last_name: document.getElementById('np_last_name')?.value || '',
            phone_number: document.getElementById('np_phone_number')?.value || '',
            current_city: document.getElementById('np_current_city')?.value || '',
        };
        const questionUpdates = {
            years_of_experience: document.getElementById('np_years_of_experience')?.value || '',
            notice_period: parseInt(document.getElementById('np_notice_period')?.value, 10) || 0,
            current_ctc: parseInt(document.getElementById('np_current_ctc')?.value, 10) || 0,
            desired_salary: parseInt(document.getElementById('np_desired_salary')?.value, 10) || 0,
            recent_employer: document.getElementById('np_recent_employer')?.value || '',
            linkedIn: document.getElementById('np_linkedIn')?.value || '',
            website: document.getElementById('np_website')?.value || '',
            default_resume_path: document.getElementById('np_default_resume_path')?.value || '',
        };
        const secretUpdates = {
            username: document.getElementById('naukri_username')?.value || '',
            password: document.getElementById('naukri_password')?.value || '',
        };

        // Parse custom answers textarea
        const customText = document.getElementById('custom_naukri_answers_text')?.value || '';
        const customDict = {};
        customText.split('\n').forEach(line => {
            const idx = line.indexOf(':');
            if (idx > 0) {
                const k = line.slice(0, idx).trim();
                const v = line.slice(idx + 1).trim();
                if (k) customDict[k] = v;
            }
        });

        const naukriQuestionUpdates = {
            willing_to_relocate: document.getElementById('willing_to_relocate')?.value || 'Yes',
            default_yes_no_answer: document.getElementById('default_yes_no_answer')?.value || 'Yes',
            pause_at_unknown_naukri_question: document.getElementById('pause_at_unknown_naukri_question')?.value === 'true',
            custom_naukri_answers: customDict,
        };

        const sections = {
            personals: personalUpdates,
            questions: questionUpdates,
            secrets: secretUpdates,
            naukri_questions: naukriQuestionUpdates,
        };

        const res = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sections }),
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.error || 'Save failed');
        showToast('Naukri Profile saved successfully!');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

/* ───── Save All + Start Bot ───── */
async function saveAllAndStart() {
    try {
        const sections = {};
        for (const section of Object.keys(sectionFields)) {
            sections[section] = collectSection(section);
        }
        const customText = document.getElementById('custom_naukri_answers_text')?.value || '';
        const customDict = {};
        customText.split('\n').forEach(line => {
            const idx = line.indexOf(':');
            if (idx > 0) customDict[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
        });
        sections.naukri_questions = { ...collectSection('naukri_questions'), custom_naukri_answers: customDict };
        const saveRes = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sections }),
        });
        if (!saveRes.ok) {
            const err = await saveRes.json();
            throw new Error(err.error || 'Failed to save config');
        }
        const startRes = await fetch('/api/bot/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ platform: selectedPlatform }),
        });
        const startResult = await startRes.json();
        if (!startRes.ok) throw new Error(startResult.error || 'Failed to start bot');
        showToast(`${selectedPlatform} bot started!`);
        updateBotStatus();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

/* ───── Unknown Questions ───── */
let unknownQuestionsData = [];

async function loadUnknownQuestions() {
    try {
        const res = await fetch('/api/naukri/unknown-questions');
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to load');

        unknownQuestionsData = data.questions || [];
        const total = data.total || 0;
        const unanswered = data.unanswered || 0;

        // Update badge
        const badge = document.getElementById('unknownBadge');
        if (badge) {
            if (unanswered > 0) {
                badge.textContent = unanswered;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }

        const tbody = document.getElementById('unknownQuestionsBody');
        const emptyEl = document.getElementById('unknownEmpty');
        const tableWrap = document.getElementById('unknownTableWrap');
        const answerBar = document.getElementById('unknownAnswerBar');

        if (!total) {
            emptyEl.style.display = 'block';
            tableWrap.style.display = 'none';
            answerBar.style.display = 'none';
            return;
        }

        emptyEl.style.display = 'none';
        tableWrap.style.display = 'block';
        answerBar.style.display = 'flex';

        tbody.innerHTML = '';
        unknownQuestionsData.forEach((q, i) => {
            const row = document.createElement('tr');
            if (q.status === 'new') row.classList.add('unanswered-row');

            const timeStr = q.time ? new Date(q.time).toLocaleDateString('en-IN', {
                day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
            }) : '—';

            const optionsStr = q.options.length ? q.options.join(', ') : '—';
            const statusHtml = q.status === 'answered'
                ? '<span class="status-answered">✓ Answered</span>'
                : '<span class="status-new">● New</span>';

            row.innerHTML = `
                <td>${i + 1}</td>
                <td class="question-cell">${escapeHtml(q.question)}</td>
                <td class="options-cell">${escapeHtml(optionsStr)}</td>
                <td>${timeStr}</td>
                <td>${statusHtml}</td>
                <td><input type="text" class="uq-keyword" data-index="${i}" value="${escapeHtml(q.matched_keyword || '')}" placeholder="keyword"></td>
                <td><input type="text" class="uq-answer" data-index="${i}" value="${escapeHtml(q.existing_answer || '')}" placeholder="your answer"></td>
            `;
            tbody.appendChild(row);
        });
    } catch (e) {
        console.error('Failed to load unknown questions:', e);
    }
}

async function saveUnknownAnswers() {
    try {
        const answers = {};
        document.querySelectorAll('.uq-answer').forEach(input => {
            const idx = parseInt(input.dataset.index, 10);
            const answer = input.value.trim();
            const keywordInput = document.querySelector(`.uq-keyword[data-index="${idx}"]`);
            let keyword = keywordInput?.value.trim() || '';

            if (!answer) return;

            // If no keyword provided, use a short version of the question text
            if (!keyword && unknownQuestionsData[idx]) {
                const q = unknownQuestionsData[idx].question.toLowerCase();
                // Extract meaningful words from the question
                keyword = q.replace(/[?.,!]/g, '').trim();
                if (keyword.length > 40) {
                    // Use first meaningful phrase
                    keyword = keyword.split(/\s+/).slice(0, 5).join(' ');
                }
            }

            if (keyword) {
                answers[keyword] = answer;
            }
        });

        if (!Object.keys(answers).length) {
            showToast('No answers to save. Fill in at least one answer.', 'error');
            return;
        }

        const res = await fetch('/api/naukri/answer-questions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answers }),
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.error || 'Save failed');
        showToast(`Saved ${Object.keys(answers).length} answer(s)!`);
        // Reload to update statuses
        await loadUnknownQuestions();
        // Also reload config to refresh custom answers textarea
        await loadConfig();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

/* ───── Load Config ───── */
async function loadConfig() {
    try {
        const res = await fetch('/api/config');
        configData = await res.json();
        const opts = configData.options || {};
        const sections = configData.sections || {};

        populateSelect('sort_by', opts.sort_by, sections.search?.sort_by);
        populateSelect('date_posted', opts.date_posted, sections.search?.date_posted);
        populateSelect('salary', opts.salary, sections.search?.salary);
        populateCheckboxes('experience_level', opts.experience_level, sections.search?.experience_level);
        populateCheckboxes('job_type', opts.job_type, sections.search?.job_type);
        populateCheckboxes('on_site', opts.on_site, sections.search?.on_site);
        populateCheckboxes('work_mode', opts.work_mode, sections.search_naukri?.work_mode);
        populateSelect('ethnicity', opts.ethnicity, sections.personals?.ethnicity);
        populateSelect('gender', opts.gender, sections.personals?.gender);
        populateSelect('disability_status', opts.disability_status, sections.personals?.disability_status);
        populateSelect('veteran_status', opts.veteran_status, sections.personals?.veteran_status);
        populateSelect('require_visa', opts.require_visa, sections.questions?.require_visa);
        populateSelect('us_citizenship', opts.us_citizenship, sections.questions?.us_citizenship);
        populateSelect('ai_provider', opts.ai_provider, sections.secrets?.ai_provider);

        // Custom Naukri answers textarea
        const customAnswers = sections.naukri_questions?.custom_naukri_answers || {};
        const customEl = document.getElementById('custom_naukri_answers_text');
        if (customEl && typeof customAnswers === 'object') {
            customEl.value = Object.entries(customAnswers).map(([k, v]) => `${k}: ${v}`).join('\n');
        }

        // Populate all standard sections
        for (const [section, fields] of Object.entries(sections)) {
            const tags = section === 'search_naukri' ? naukriTagFields : tagFields;
            for (const [key, value] of Object.entries(fields)) {
                if (key.endsWith('_set')) continue;
                if (tags[key]) {
                    createTagInput(tags[key], key, value || []);
                } else {
                    const domId = section === 'search_naukri' ? naukriDomId(key) : key;
                    if (!multiSelectFields.includes(key) && document.getElementById(domId)) {
                        setFieldValue(domId, value);
                    }
                }
            }
        }

        // Populate Naukri Profile tab fields (mirrored from config sections)
        const p = sections.personals || {};
        const q = sections.questions || {};
        const s = sections.secrets || {};
        const nq = sections.naukri_questions || {};

        // Login credentials
        setFieldValue('naukri_username', s.username || '');
        // Don't fill password for security

        // Personal details
        setFieldValue('np_first_name', p.first_name || '');
        setFieldValue('np_middle_name', p.middle_name || '');
        setFieldValue('np_last_name', p.last_name || '');
        setFieldValue('np_phone_number', p.phone_number || '');
        setFieldValue('np_current_city', p.current_city || '');
        setFieldValue('np_years_of_experience', q.years_of_experience || '');
        setFieldValue('np_notice_period', q.notice_period || 0);
        setFieldValue('np_current_ctc', q.current_ctc || 0);
        setFieldValue('np_desired_salary', q.desired_salary || 0);
        setFieldValue('np_recent_employer', q.recent_employer || '');
        setFieldValue('np_linkedIn', q.linkedIn || '');
        setFieldValue('np_website', q.website || '');
        setFieldValue('np_default_resume_path', q.default_resume_path || '');

        // Recruiter questions
        setFieldValue('willing_to_relocate', nq.willing_to_relocate || 'Yes');
        setFieldValue('default_yes_no_answer', nq.default_yes_no_answer || 'Yes');
        setFieldValue('pause_at_unknown_naukri_question', nq.pause_at_unknown_naukri_question ? 'true' : 'false');

    } catch (e) {
        showToast('Failed to load config: ' + e.message, 'error');
    }
}

/* ───── Bot Status ───── */
async function updateBotStatus() {
    try {
        const res = await fetch('/api/bot/status');
        const { running, platform } = await res.json();
        const dot = document.getElementById('statusDot');
        const text = document.getElementById('statusText');
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        if (running) {
            dot.classList.add('running');
            text.textContent = `Running (${platform || 'bot'})`;
            startBtn.style.display = 'none';
            stopBtn.style.display = 'inline-block';
        } else {
            dot.classList.remove('running');
            text.textContent = 'Idle';
            startBtn.style.display = 'inline-block';
            stopBtn.style.display = 'none';
        }
    } catch (_) { /* ignore */ }
}

document.getElementById('startBtn').addEventListener('click', saveAllAndStart);
document.getElementById('stopBtn').addEventListener('click', async () => {
    try {
        const res = await fetch('/api/bot/stop', { method: 'POST' });
        const result = await res.json();
        if (!res.ok) throw new Error(result.error);
        showToast('Bot stopped');
        updateBotStatus();
    } catch (e) {
        showToast(e.message, 'error');
    }
});

/* ───── Applied Jobs History ───── */
let jobsData = [];
async function loadJobs() {
    try {
        const res = await fetch('/applied-jobs');
        const tbody = document.getElementById('jobsBody');
        const empty = document.getElementById('jobsEmpty');
        if (!res.ok) {
            empty.style.display = 'block';
            tbody.innerHTML = '';
            return;
        }
        jobsData = await res.json();
        const filter = document.getElementById('historyPlatformFilter')?.value || '';
        const filtered = filter ? jobsData.filter(j => j.Platform === filter) : jobsData;
        tbody.innerHTML = '';
        if (!filtered.length) {
            empty.style.display = 'block';
            return;
        }
        empty.style.display = 'none';
        filtered.forEach((job, i) => tbody.appendChild(createJobRow(job, i)));
    } catch (e) {
        document.getElementById('jobsEmpty').style.display = 'block';
    }
}

function createJobRow(job, index) {
    const row = document.createElement('tr');
    const appliedCell = document.createElement('td');
    const extCell = document.createElement('td');

    row.innerHTML = `
        <td>${index + 1}</td>
        <td><span class="platform-tag">${escapeHtml(job.Platform || 'LinkedIn')}</span></td>
        <td><a href="${job.Job_Link}" target="_blank">${escapeHtml(job.Title)}</a></td>
        <td>${escapeHtml(job.Company)}</td>
        <td>${job.HR_Name && job.HR_Name !== 'Unknown'
            ? `<a href="${job.HR_Link}" target="_blank">${escapeHtml(job.HR_Name)}</a>` : 'N/A'}</td>
    `;
    row.appendChild(extCell);
    row.appendChild(appliedCell);

    const ext = job.External_Job_link || '';
    if (ext === 'Easy Applied' || ext === 'Applied on Naukri') {
        extCell.textContent = ext;
        appliedCell.innerHTML = '<span class="tick">✓</span>';
    } else if (ext && ext !== 'Pending') {
        const link = document.createElement('a');
        link.href = ext;
        link.textContent = 'External Link';
        link.target = '_blank';
        link.addEventListener('click', async () => {
            const res = await fetch(`/applied-jobs/${job.Job_ID}`, { method: 'PUT' });
            if (res.ok) appliedCell.innerHTML = '<span class="tick">✓</span>';
        });
        extCell.appendChild(link);
        if (job.Date_Applied !== 'Pending') appliedCell.innerHTML = '<span class="tick">✓</span>';
    } else {
        extCell.textContent = ext || 'N/A';
        if (job.Date_Applied && job.Date_Applied !== 'Pending') appliedCell.innerHTML = '<span class="tick">✓</span>';
    }
    return row;
}

/* ───── Init ───── */
loadConfig();
updateBotStatus();
setInterval(updateBotStatus, 5000);

// Load unknown questions badge count on startup
(async () => {
    try {
        const res = await fetch('/api/naukri/unknown-questions');
        const data = await res.json();
        if (res.ok && data.unanswered > 0) {
            const badge = document.getElementById('unknownBadge');
            if (badge) {
                badge.textContent = data.unanswered;
                badge.style.display = 'inline-block';
            }
        }
    } catch (_) { /* ignore */ }
})();
