import os
import re

tests_dir = "tests"
for root, _, files in os.walk(tests_dir):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            content = re.sub(r"patch\(['\"]com\.", r"patch('src.com.", content)
            content = re.sub(r"patch\(['\"]logic\.", r"patch('src.logic.", content)
            content = re.sub(r"patch\(['\"]repositories\.", r"patch('src.repositories.", content)
            content = re.sub(r"patch\(['\"]services\.", r"patch('src.services.", content)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

print("Patch replacements completed.")
