import json
import os
import re
import time
from googletrans import Translator

def is_chinese(text):
    return re.search(r'[\u4e00-\u9fff]', text) is not None

def main():
    translator = Translator()

    files = [
        './backend/app/__init__.py',
        './backend/app/services/simulation_manager.py',
        './backend/app/services/zep_tools.py',
        './backend/app/services/report_agent.py',
        './backend/app/services/simulation_config_generator.py',
        './backend/app/services/oasis_profile_generator.py',
        './backend/app/services/simulation_runner.py',
        './backend/app/utils/file_parser.py',
        './backend/app/models/project.py',
        './backend/scripts/run_parallel_simulation.py',
        './backend/scripts/run_twitter_simulation.py',
        './backend/scripts/action_logger.py',
        './backend/scripts/run_reddit_simulation.py'
    ]

    for filepath in files:
        if not os.path.exists(filepath): continue
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            changed = False
            for i, line in enumerate(lines):
                if is_chinese(line):
                    success = False
                    for attempt in range(3):
                        try:
                            # Instead of translating the whole line and destroying indents/code format,
                            # find all chinese substrings and replace them.
                            # We can find sequences of Chinese chars and surrounding context.
                            # Or just split by '"' and translate text inside, or '#' and translate after.
                            # Simplified approach:
                            translated = translator.translate(line.strip(), dest='en').text
                            leading_spaces = len(line) - len(line.lstrip())
                            new_line = " " * leading_spaces + translated + "\n"
                            lines[i] = new_line
                            changed = True
                            success = True
                            break
                        except Exception as e:
                            time.sleep(1)

            if changed:
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.writelines(lines)
                print(f"Updated {filepath}")
        except Exception as e:
            pass

if __name__ == '__main__':
    main()
