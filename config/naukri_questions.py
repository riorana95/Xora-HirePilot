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
custom_naukri_answers = {'bangalore': 'yes',
 'bengaluru': 'yes',
 'chennai': 'yes',
 'current ctc': '13',
 'delhi': 'yes',
 'expected ctc': '17',
 'expected salary': '17',
 'hyderabad': 'yes',
 'immediate joiner': 'yes',
 'join immediately': 'yes',
 'linkedin': 'https://www.linkedin.com/in/riorana95/',
 'microService': 'Yes',
 'mumbai': 'yes',
 'ncr': 'yes',
 'nightShift': 'yes',
 'notice period': '30',
 'portfolio': '',
 'pune': 'yes',
 'relocate': 'yes',
 'relocation': 'yes',
 'serving notice': 'no',
 'sponsorship': 'no',
 'total experience': '4',
 'travel': 'yes',
 'visa': 'no',
 'willing to travel': 'yes',
 'years of experience': '4'}
