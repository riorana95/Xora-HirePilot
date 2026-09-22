'''
Develop by Rana Rahul

Centralized Naukri.com DOM selectors — update here when Naukri changes layout.
'''

# URLs
LOGIN_URL = "https://www.naukri.com/nlogin/login"
HOME_URL = "https://www.naukri.com/mnjuser/homepage"
SEARCH_BASE = "https://www.naukri.com"

# Login / session
LOGGED_IN_INDICATORS = [
    "//div[contains(@class,'nI-gNb-drawer')]",
    "//a[contains(@class,'nI-gNb-avatar')]",
    "//div[contains(@class,'user-name')]",
    "//span[contains(@class,'nI-gNb-user')]",
    "//a[contains(@href,'/mnjuser')]",
]
LOGIN_BUTTON = [
    "//a[contains(text(),'Login')]",
    "//button[contains(text(),'Login')]",
    "//a[contains(@href,'nlogin')]",
]
GOOGLE_SIGN_IN = [
    "//button[contains(@class,'google')]",
    "//div[contains(@class,'google')]",
    "//span[contains(text(),'Google')]/ancestor::button",
    "//button[contains(.,'Google')]",
    "//a[contains(.,'Google')]",
]
EMAIL_INPUT = [
    "//input[@type='text' and contains(@placeholder,'Email')]",
    "//input[@type='email']",
    "//input[contains(@id,'usernameField')]",
    "//input[contains(@name,'username')]",
    "//input[contains(@placeholder,'email')]",
]
PASSWORD_INPUT = [
    "//input[@type='password']",
    "//input[contains(@id,'passwordField')]",
    "//input[contains(@name,'password')]",
]
LOGIN_SUBMIT = [
    "//button[contains(text(),'Login')]",
    "//button[@type='submit']",
    "//button[contains(text(),'login')]",
    "//button[contains(@class,'login')]",
]

# Search
SEARCH_KEYWORD_INPUT = [
    "//input[contains(@placeholder,'skills') or contains(@placeholder,'designation') or contains(@placeholder,'Search')]",
    "//input[@class='suggestor-input']",
    "//input[contains(@id,'qsb')]",
]
SEARCH_LOCATION_INPUT = [
    "//input[contains(@placeholder,'location') or contains(@placeholder,'Location')]",
    "//input[contains(@class,'location')]",
]
SEARCH_SUBMIT = [
    "//button[contains(text(),'Search')]",
    "//button[@type='submit']",
    "//div[contains(@class,'qsbSubmit')]",
]

# Job listings
JOB_CARD = [
    "//div[contains(@class,'srp-jobtuple-wrapper')]",
    "//article[contains(@class,'jobTuple')]",
    "//div[contains(@class,'cust-job-tuple')]",
    "//div[contains(@class,'jobTuple')]",
    "//div[contains(@class,'job-card')]",
    "//div[contains(@class,'list-item')]",
    "//article[contains(@class,'job')]",
    "//div[@data-job-id]",
]
JOB_TITLE = [".//a[contains(@class,'title')]", ".//a[contains(@class,'jobTitle')]", ".//h2/a", ".//a[contains(@href,'job-listings')]", ".//a[contains(@class,'info')]", ".//h2"]
JOB_COMPANY = [".//a[contains(@class,'comp')]", ".//span[contains(@class,'comp')]", ".//a[contains(@class,'subTitle')]", ".//span[contains(@class,'company')]", ".//a[contains(@class,'company')]"]
JOB_LOCATION = [".//span[contains(@class,'loc')]", ".//li[contains(@class,'location')]", ".//span[contains(@class,'location')]", ".//span[contains(@class,'place')]"]
JOB_EXPERIENCE = [".//span[contains(@class,'exp')]", ".//li[contains(@class,'experience')]", ".//span[contains(@class,'experience')]"]
JOB_SALARY = [".//span[contains(@class,'sal')]", ".//li[contains(@class,'salary')]", ".//span[contains(@class,'salary')]"]
JOB_LINK = [".//a[contains(@class,'title')]", ".//a[contains(@href,'job-listings')]", ".//h2/a", ".//a[contains(@class,'info')]"]

# Apply
APPLY_BUTTON = [
    ".//button[contains(text(),'Apply')]",
    ".//a[contains(text(),'Apply')]",
    ".//button[contains(@class,'apply')]",
    ".//a[contains(@class,'apply')]",
]
ALREADY_APPLIED = [
    ".//button[contains(text(),'Applied')]",
    ".//span[contains(text(),'Applied')]",
    ".//a[contains(text(),'Applied')]",
]
EXTERNAL_APPLY = [
    ".//button[contains(text(),'Apply on company site')]",
    ".//a[contains(text(),'Apply on company site')]",
    ".//span[contains(text(),'Apply on company site')]",
]

# Job detail page
JOB_DESCRIPTION = [
    "//div[contains(@class,'job-desc')]",
    "//div[contains(@class,'dang-inner-html')]",
    "//section[contains(@class,'job-desc')]",
    "//div[contains(@class,'JDC')]",
]

# Recruiter chat questionnaire (Apply → one question at a time → Save)
RECRUITER_CHAT_MODAL = [
    # Current Naukri recruiter drawer uses generated chatbot_* class names.
    "//*[contains(@class,'chatbot') and .//input[not(@type='hidden')]]",
    "//div[contains(.,\"recruiter's questions\")]",
    "//div[contains(.,'Kindly answer')]",
    "//div[contains(.,'thank you for showing interest')]",
    "//div[contains(@class,'chat') and contains(@class,'modal')]",
    "//div[contains(@class,'applyQues')]",
    "//div[contains(@class,'questionnaire')]",
    # Naukri also shows application questions in a right-side drawer rather
    # than a chat popup. Limit this to panels that actually contain fields.
    "//div[@role='dialog' and (.//input or .//textarea or .//select)]",
    "//aside[contains(@class,'drawer') and (.//input or .//textarea or .//select)]",
    "//div[contains(@class,'drawer') and (.//input or .//textarea or .//select)]",
    "//div[contains(@class,'apply') and (.//input or .//textarea or .//select)]",
    "//div[.//input[not(@type='hidden')] and .//button[normalize-space()='Save']]",
]
RECRUITER_QUESTION_TEXT = [
    ".//div[contains(@class,'message')]",
    ".//div[contains(@class,'bubble')]",
    ".//div[contains(@class,'question')]",
    ".//p[contains(.,'?')]",
    ".//span[contains(.,'?')]",
    ".//label",
    ".//*[not(*) and contains(normalize-space(.), '?')]",
]
RECRUITER_SAVE_BUTTON = [
    "//button[normalize-space()='Save']",
    "//button[contains(.,'Save & Continue')]",
    "//button[contains(.,'Continue')]",
    "//button[contains(.,'Next')]",
    "//button[contains(text(),'Save')]",
    "//button[contains(@class,'save')]",
]

# Standard application form (non-chat)
FORM_CONTAINER = [
    "//div[contains(@class,'apply-modal')]",
    "//div[contains(@class,'application')]",
    "//form[contains(@class,'apply')]",
    "//div[contains(@id,'apply')]",
]
FORM_INPUT = ".//input[@type='text' or @type='number' or @type='email' or @type='tel' or not(@type)]"
FORM_TEXTAREA = ".//textarea"
FORM_SELECT = ".//select"
FORM_RADIO = ".//input[@type='radio']"
FORM_CHECKBOX = ".//input[@type='checkbox']"
FORM_SUBMIT = [
    "//button[contains(text(),'Submit')]",
    "//button[contains(text(),'Apply')]",
    "//button[contains(text(),'Save')]",
    "//button[contains(@class,'submit')]",
]
FORM_NEXT = [
    "//button[contains(text(),'Next')]",
    "//button[contains(text(),'Continue')]",
]
FORM_CLOSE = [
    "//button[contains(@class,'close')]",
    "//span[contains(@class,'close')]",
    "//button[contains(@aria-label,'close')]",
]
RESUME_UPLOAD = [
    "//input[@type='file']",
    "//input[contains(@name,'resume')]",
    "//input[contains(@name,'file')]",
]

# Pagination
NEXT_PAGE = [
    "//a[contains(@class,'fright') and contains(@class,'next')]",
    "//a[span[contains(text(),'Next')]]",
    "//a[contains(text(),'Next')]",
    "//button[contains(text(),'Next')]",
]

# Filters sidebar
FILTER_EXPERIENCE = "//span[contains(text(),'Experience')]/ancestor::div[contains(@class,'filter')]"
FILTER_SALARY = "//span[contains(text(),'Salary')]/ancestor::div[contains(@class,'filter')]"
FILTER_WFH = "//span[contains(text(),'Work from home') or contains(text(),'Remote')]/ancestor::div[contains(@class,'filter')]"

# Naukri frequently changes filter section class names.
# The URL-param approach in search.py is the primary method.
# These are secondary selectors for sidebar reinforcement.
FILTER_WORK_MODE = [
    "//span[contains(text(),'Work Mode')]/ancestor::div[contains(@class,'filter')]",
    "//span[contains(text(),'Work from home')]/ancestor::div[contains(@class,'filter')]",
    "//span[contains(text(),'Remote')]/ancestor::div[contains(@class,'filter')]",
]
FILTER_FRESHNESS = [
    "//span[contains(text(),'Freshness')]/ancestor::div[contains(@class,'filter')]",
    "//span[contains(text(),'Date Posted')]/ancestor::div[contains(@class,'filter')]",
]
FILTER_LOCATION = [
    "//span[contains(text(),'Location')]/ancestor::div[contains(@class,'filter')]",
]
FILTER_DEPARTMENT = [
    "//span[contains(text(),'Department')]/ancestor::div[contains(@class,'filter')]",
]
FILTER_COMPANY_TYPE = [
    "//span[contains(text(),'Company type')]/ancestor::div[contains(@class,'filter')]",
    "//span[contains(text(),'Company Type')]/ancestor::div[contains(@class,'filter')]",
]
