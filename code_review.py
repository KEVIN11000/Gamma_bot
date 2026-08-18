# code_review.py
"""Simple code‑review script for the Gamma_bot project.
It performs:
  • A recursive search for "TODO"/comments that may indicate unfinished work.
  • Runs `flake8` (if available) to report style warnings.
  • Generates a markdown report `code_review_v1.0.0.md`.
"""
import pathlib
import subprocess


def find_todos(root: pathlib.Path) -> list[str]:
    todos = []
    for py_file in root.rglob("*.py"):
        with py_file.open(encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                if "TODO" in line:
                    todos.append(f"- {py_file.relative_to(root)}:{i}: {line.strip()}")
    return todos


def run_flake8(root: pathlib.Path) -> str:
    try:
        result = subprocess.run(
            ["flake8", str(root)], capture_output=True, text=True, check=False
        )
        return result.stdout.strip()
    except FileNotFoundError:
        return "flake8 not installed."


def main():
    repo_root = pathlib.Path(__file__).parent
    todos = find_todos(repo_root)
    flake8_report = run_flake8(repo_root)
    report_path = repo_root / "code_review_v1.0.0.md"
    with report_path.open("w", encoding="utf-8") as out:
        out.write("# Code Review Report (v1.0.0)\n\n")
        out.write("## TODO entries found\n")
        if todos:
            out.write("\n".join(todos))
        else:
            out.write("None.\n")
        out.write("\n\n## flake8 report\n")
        out.write(f"```\n{flake8_report}\n```")
    print("Report written to", report_path)


if __name__ == "__main__":
    main()
