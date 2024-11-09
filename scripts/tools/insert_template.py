import re
from datetime import datetime

def insert_data(template_file, output_file, data):
    # Read the template file
    with open(template_file, 'r') as file:
        template = file.read()
    
    # Replace all marked places with corresponding data
    for key, value in data.items():
        pattern = r'\{\{\s*' + re.escape(key) + r'\s*\}\}'
        template = re.sub(pattern, str(value), template)
    
    # Write the result to the output file
    with open(output_file, 'w') as file:
        file.write(template)

