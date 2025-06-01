import argparse
from pathlib import Path
import subprocess
import sys


def check_repository():
    project_root = Path(__file__).parent / "StarRailCopilot"

    if not project_root.exists() or not (project_root / ".git").exists():
        print("StarRailCopilot repository not found, cloning...")
        try:
            subprocess.run(
                [
                    "git",
                    "clone",
                    "https://github.com/LmeSzinc/StarRailCopilot.git",
                    str(project_root),
                ],
                check=True,
                cwd=Path(__file__).parent,
            )
            print("Successfully cloned StarRailCopilot repository")
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone StarRailCopilot repository: {e}")
            print("Please manually clone the repository:")
            print("git clone https://github.com/LmeSzinc/StarRailCopilot.git")
            sys.exit(1)
        except FileNotFoundError:
            print("Git is not installed or not in PATH")
            print("Please install Git and try again, or manually clone the repository:")
            print("git clone https://github.com/LmeSzinc/StarRailCopilot.git")
            sys.exit(1)


if __name__ == "__main__":
    check_repository()

    parser = argparse.ArgumentParser()
    parser.add_argument("config_name")
    parser.add_argument("task_name")
    args = parser.parse_args()

    from adapter import Adapter

    adapter = Adapter(args.config_name)
    adapter.dacapo_task(args.task_name)
