/* Develop by Rana Rahul */
let configData = {};
let selectedPlatform = 'naukri'; // header platform selector for bot start
let currentProfileId = '';
let profilesIndex = { active: '', profiles: [] };

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
        'about_company_bad_words', 'bad_title_words', 'bad_words', 'security_clearance', 'did_masters', 'current_experience',
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
    setTimeout(() => { toast.className = 'toast'; }, 3000);
}

function escapeHtml(text) {
    if (typeof text !== 'string') return '';
    return text.replace(/[&<>'"]/g, tag => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[tag] || tag));
}

function createTagInput(containerId, fieldName, values = []) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = '';
    const tagsWrapper = document.createElement('div');
    tagsWrapper.className = 'tags-wrapper';
    
    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = `Add ${fieldName.replace(/_/g, ' ')}... (press Enter)`;
    
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
        el.value = value || '';
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
    return el.type === 'number' ? (el.value ? Number(el.value) : 0) : el.value;
}

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
        
        // Identity
        ['first_name', 'middle_name', 'last_name', 'phone_number', 'current_city',
         'street', 'state', 'zipcode', 'country', 'gender', 'ethnicity', 
         'disability_status', 'veteran_status'].forEach(f => {
            setFieldValue(f, profile.identity?.[f] || '');
        });
        
        // Credentials
        setFieldValue('prof_linkedin_email', profile.credentials?.linkedin_email || '');
        setFieldValue('prof_naukri_email', profile.credentials?.naukri_email || '');
        document.getElementById('prof_linkedin_password').value = '';
        document.getElementById('prof_naukri_password').value = '';
        
        // Professional
        ['years_of_experience', 'current_ctc', 'desired_salary', 'notice_period',
         'recent_employer', 'linkedIn', 'website', 'default_resume_path',
         'linkedin_headline', 'linkedin_summary', 'cover_letter', 
         'user_information_all', 'confidence_level'].forEach(f => {
            setFieldValue(f, profile.professional?.[f] || '');
        });
        
        // QA
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
    const data = {
        identity: {},
        credentials: {},
        professional: {},
        qa: {}
    };
    
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
        const res = await fetch(`/api/profiles/${currentProfileId}`, {
            method: 'DELETE'
        });
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
            showToast(`Bot config saved successfully`);
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
        
        // Populate profile dropdown options (though profile handles its own loading, we can populate global selects)
        populateSelect('gender', options.gender || []);
        populateSelect('ethnicity', options.ethnicity || []);
        populateSelect('disability_status', options.disability_status || []);
        populateSelect('veteran_status', options.veteran_status || []);
        populateSelect('require_visa', options.require_visa || []);
        populateSelect('us_citizenship', options.us_citizenship || []);
        
        // Populate filter dropdown options
        populateSelect('sort_by', options.sort_by || []);
        populateSelect('date_posted', options.date_posted || []);
        populateSelect('salary', options.salary || []);
        populateSelect('freshness', options.date_posted || []); // Reusing date_posted for freshness
        populateSelect('ai_provider', options.ai_provider || []);
        
        // Populate Checkboxes
        populateCheckboxes('experience_level', options.experience_level || [], configData.sections?.search?.experience_level || []);
        populateCheckboxes('job_type', options.job_type || [], configData.sections?.search?.job_type || []);
        populateCheckboxes('on_site', options.on_site || [], configData.sections?.search?.on_site || []);
        populateCheckboxes('work_mode', options.work_mode || [], configData.sections?.search_naukri?.work_mode || []);

        const sections = configData.sections || {};
        
        // Populate normal fields and tags
        ['search', 'search_naukri', 'settings', 'secrets'].forEach(sec => {
            const data = sections[sec] || {};
            sectionFields[sec].forEach(f => {
                let idToUse = sec === 'search_naukri' ? naukriDomId(f) : f;
                
                if (tagFields[f] && sec === 'search') {
                    createTagInput(tagFields[f], f, data[f] || []);
                } else if (naukriTagFields[f] && sec === 'search_naukri') {
                    createTagInput(naukriTagFields[f], f, data[f] || []);
                } else if (!multiSelectFields.includes(f)) {
                    if (f !== 'llm_api_key') { // Don't populate API key
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
    } catch (error) {
        console.error('Error fetching bot status:', error);
    }
}

async function startBot() {
    const platform = document.getElementById('platformSelect').value;
    try {
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
        }
    } catch (error) {
        showToast('Error starting bot', 'error');
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

async function loadJobs() {
    try {
        const response = await fetch('/applied-jobs');
        const jobs = await response.json();
        
        const platformFilter = document.getElementById('historyPlatformFilter').value;
        const tbody = document.getElementById('jobsBody');
        const emptyState = document.getElementById('jobsEmpty');
        
        let filteredJobs = jobs;
        if (platformFilter) {
            filteredJobs = jobs.filter(j => (j.platform || 'LinkedIn').toLowerCase() === platformFilter.toLowerCase());
        }
        
        if (filteredJobs.length === 0) {
            tbody.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }
        
        emptyState.style.display = 'none';
        
        tbody.innerHTML = filteredJobs.map((job, index) => createJobRow(job, index)).join('');
    } catch (error) {
        console.error('Error loading jobs:', error);
    }
}

function createJobRow(job, index) {
    const date = new Date(job.timestamp).toLocaleString();
    const plat = job.platform || 'LinkedIn';
    const platClass = plat.toLowerCase() === 'naukri' ? 'plat-naukri' : 'plat-linkedin';
    return `
        <tr>
            <td>${index + 1}</td>
            <td><span class="platform-badge ${platClass}">${plat}</span></td>
            <td><strong>${escapeHtml(job.job_title)}</strong></td>
            <td>${escapeHtml(job.company_name)}</td>
            <td>${job.hr_name ? escapeHtml(job.hr_name) : '-'}</td>
            <td><a href="${escapeHtml(job.job_url)}" target="_blank" class="btn btn-outline btn-sm">View Job</a></td>
            <td>${date}</td>
        </tr>
    `;
}

async function loadUnknownQuestions() {
    try {
        const res = await fetch('/api/naukri/unknown-questions');
        const data = await res.json();
        
        const empty = document.getElementById('unknownEmpty');
        const table = document.getElementById('unknownTableWrap');
        const bar = document.getElementById('unknownAnswerBar');
        const tbody = document.getElementById('unknownQuestionsBody');
        
        if (data.questions.length === 0) {
            empty.style.display = 'block';
            table.style.display = 'none';
            bar.style.display = 'none';
            return;
        }
        
        empty.style.display = 'none';
        table.style.display = 'block';
        bar.style.display = 'flex';
        
        tbody.innerHTML = data.questions.map((q, idx) => `
            <tr data-question-id="${idx}">
                <td>${idx + 1}</td>
                <td style="max-width: 300px; word-wrap: break-word;">${escapeHtml(q.question)}</td>
                <td style="max-width: 200px; word-wrap: break-word;">${q.options ? escapeHtml(q.options.join(', ')) : 'N/A'}</td>
                <td>${new Date(q.discovered_at).toLocaleString()}</td>
                <td>
                    ${q.status === 'answered' ? '<span class="status-badge" style="background:#10b981;padding:2px 6px;border-radius:4px;color:white;font-size:12px;">Answered</span>' : '<span class="status-badge" style="background:#f59e0b;padding:2px 6px;border-radius:4px;color:white;font-size:12px;">Pending</span>'}
                </td>
                <td><input type="text" class="uq-keyword form-control" placeholder="keyword" style="width: 120px;" value="${escapeHtml(q.suggested_keyword || '')}"></td>
                <td><input type="text" class="uq-answer form-control" placeholder="your answer" style="width: 150px;"></td>
            </tr>
        `).join('');
        
    } catch (err) {
        console.error('Error loading unknown questions', err);
    }
}

async function saveUnknownAnswers() {
    const answers = {};
    document.querySelectorAll('#unknownQuestionsBody tr').forEach(tr => {
        const keyword = tr.querySelector('.uq-keyword').value.trim();
        const answer = tr.querySelector('.uq-answer').value.trim();
        if (keyword && answer) {
            answers[keyword] = answer;
        }
    });
    
    if (Object.keys(answers).length === 0) {
        showToast('No valid answers provided', 'error');
        return;
    }
    
    try {
        const res = await fetch('/api/naukri/answer-questions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answers })
        });
        
        if (res.ok) {
            showToast('Answers saved to active profile');
            await loadUnknownQuestions();
            await loadProfile(currentProfileId); // Refresh profile form custom answers
        } else {
            showToast('Failed to save answers', 'error');
        }
    } catch (err) {
        showToast('Error saving answers', 'error');
    }
}

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
        if (btn.dataset.tab === 'history') loadJobs();
        if (btn.dataset.tab === 'config') loadUnknownQuestions();
    });
});

document.addEventListener('DOMContentLoaded', () => {
    loadProfiles();
    loadConfig();
    updateBotStatus();
    setInterval(updateBotStatus, 5000);
});
