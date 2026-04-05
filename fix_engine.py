import re

# Read the file with UTF-8 encoding
with open(r'c:\Users\lionn\Desktop\New folder\crypto_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the problematic lines
new_lines = []
i = 0
while i < len(lines):
    if '# Initialize client' in lines[i] and i + 1 < len(lines) and 'reconnect_client(use_testnet=True)' in lines[i + 1]:
        # Add the comment line
        new_lines.append(lines[i])
        # Add error handling
        new_lines.append('try:\n')
        new_lines.append('    ' + lines[i + 1])
        new_lines.append('except Exception as e:\n')
        new_lines.append('    logger.warning(f"Could not connect to Binance on startup: {e}")\n')
        new_lines.append('    logger.warning("Will attempt connection on first use, or using MockClient")\n')
        new_lines.append('    client = MockClient()\n')
        i += 2  # Skip the original reconnect line
    else:
        new_lines.append(lines[i])
        i += 1

# Write back with UTF-8 encoding
with open(r'c:\Users\lionn\Desktop\New folder\crypto_engine.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('OK: File patched successfully')
