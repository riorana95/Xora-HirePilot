'''
Develop by Rana Rahul

Naukri recruiter questionnaire answers — partial-match keys against question text.
'''

# Willing to relocate? Used when question contains "relocate" or "relocation"
willing_to_relocate = 'Yes'

# Fallback for yes/no questions with no configured match
default_yes_no_answer = 'Yes'

# Ask for an answer when an unknown question is encountered, then save it for future applications.
pause_at_unknown_naukri_question = False

# Custom answers: key is matched as substring in question text (case-insensitive), value is the answer to select/type
# Example from screenshot: "Are you willing to relocate to Hyderabad?" → matches "relocate" or "hyderabad"
custom_naukri_answers = {'noticPeriod': '90 days', 'nightShift': 'yes', 'microArch': 'yes'}
