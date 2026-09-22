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
experience_max = 4

# Salary filter in LPA — set to 0 to skip
salary_min_lpa = 0
salary_max_lpa = 0

# Work mode filter: "Remote", "Hybrid", "Office" — leave [] to skip
work_mode = []

# Only show jobs posted within last N days (3, 7, 15, 30) — set 0 to skip
job_age_days = 7

# Additional Naukri sidebar filters. Leave a list empty (or freshness blank)
# to avoid applying that filter.
freshness = ''
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

## >>>>>>>>>>> SKIP IRRELEVANT JOBS <<<<<<<<<<<

about_company_bad_words = []
about_company_good_words = []
# Skip a listing immediately when one of these phrases appears in its title.
# Example: ['.net', 'python'] avoids ".NET + Angular" and Python roles.
bad_title_words = ['.net', 'python', 'C#']
bad_words = []
security_clearance = False
did_masters = False
current_experience = 5
