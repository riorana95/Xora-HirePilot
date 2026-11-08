'''
Develop by Rana Rahul

Auto LinkedIn Job Applier - Naukri Search Preferences
'''

###################################################### NAUKRI SEARCH PREFERENCES ######################################################

# Job titles / keywords to search on Naukri
search_terms = ['Angular Developer', 'Full Stack']

# Cities or regions to search (bot runs one location per search term cycle)
search_locations = ['Bengaluru']

# Randomize search term order
randomize_search_order = False

# Max applications per keyword+location combination before switching
max_applications_per_search = 50

# Experience filter (years) — set to -1 to skip filter
experience_min = 3
experience_max = 6

# Salary filter in LPA — set to 0 to skip
salary_min_lpa = 0
salary_max_lpa = 0

# Work mode filter: "Remote", "Hybrid", "Office" — leave [] to skip
work_mode = []

# Only show jobs posted within last N days (3, 7, 15, 30) — set 0 to skip
job_age_days = 7

# Additional Naukri sidebar filters. Leave a list empty (or freshness blank)
# to avoid applying that filter.
freshness = 'Past week'
filter_locations = []
departments = []
salary_ranges = []
company_types = []
role_categories = []
educations = []
posted_by = []
industries = []
top_companies = []

# Only apply to jobs with Apply on Naukri (skip external company-site applies)
apply_on_naukri_only = True

# Pause after filters so you can review results manually
pause_after_filters = False

# Run continuously cycling search terms
run_non_stop = True

# Give up on a job after this many failed attempts (counted across runs, from
# the failed-applications CSV). 2 means one automatic retry. Set it higher to
# be more stubborn about flaky pages, or 0 to never retry a failed job.
failed_job_retry_limit = 2

# Minutes to wait between full search cycles when run_non_stop is True, so the
# bot does not hammer Naukri with back-to-back identical scans.
nonstop_cycle_gap_minutes = 15

## >>>>>>>>>>> SKIP IRRELEVANT JOBS <<<<<<<<<<<

# Companies to completely avoid — any job from these companies will be skipped
avoid_companies = []

about_company_bad_words = []
about_company_good_words = []
# Skip a listing immediately when one of these phrases appears in its title.
# Example: ['.net', 'python'] avoids ".NET + Angular" and Python roles.
bad_title_words = ['.net', 'python', 'C#']
bad_words = []
security_clearance = False
did_masters = False
current_experience = 5

# --- Optional skill-match filter ---
# Skills that, when clearly required by a JD (2+ of them mentioned), are checked
# against possessed_skills. Leave empty to disable skill filtering entirely.
required_skills = []
# Skills you actually have. A JD that requires a watched skill NOT in this list
# is skipped with reason "Skill mismatch" naming the missing skills.
possessed_skills = ['Angular', 'TypeScript', 'JavaScript', 'Java', 'Spring Boot', 'HTML', 'CSS']
