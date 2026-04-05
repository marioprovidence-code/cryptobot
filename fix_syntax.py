#!/usr/bin/env python
import re

filepath = r'c:\Users\lionn\Desktop\build\crypto_bot.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix: if __name__ == "__main__" (missing colon)
# Also need to add newline before it and indent following code
content = content.replace(
    '            logger.info("Live thread joined. Exiting.")if __name__ == "__main__"',
    '            logger.info("Live thread joined. Exiting.")\n\nif __name__ == "__main__":'
)

# Now indent all the code after if __name__ == "__main__": until the end
lines = content.split('\n')
output_lines = []
in_main_block = False
found_main = False

for i, line in enumerate(lines):
    if 'if __name__ == "__main__":' in line and not found_main:
        output_lines.append(line)
        in_main_block = True
        found_main = True
        continue
    
    if in_main_block and line and not line[0].isspace() and line.strip():
        # This line is not indented and is not empty, so main block might be ending
        # But we should indent everything that follows until end of file
        in_main_block = True  # Actually, keep indenting to end
    
    if in_main_block and line.strip():  # If in main block and line is not empty
        if not line.startswith('    '):  # If not already indented with at least 4 spaces
            output_lines.append('    ' + line)
        else:
            output_lines.append(line)
    else:
        output_lines.append(line)

fixed_content = '\n'.join(output_lines)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("File fixed successfully!")