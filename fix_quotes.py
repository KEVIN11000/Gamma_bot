import os
import re

tests_dir = "tests"
for root, _, files in os.walk(tests_dir):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            content = re.sub(r"patch\('src\.([^'\"]+)\"\)", r"patch('src.\1')", content)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

print("Quotes fixed.")
