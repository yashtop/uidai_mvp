# server/scripts/test_runner.py
import os, shutil
from pathlib import Path
from src.tools.runner import run_playwright_tests
from src.tools.generator import generate_tests

# Create a simple generated tests folder manually for fast testing:
example_dir = Path("/tmp/example_generated_tests")
if example_dir.exists():
    shutil.rmtree(example_dir)
example_tests = example_dir / "tests"
example_tests.mkdir(parents=True, exist_ok=True)

# create simple pytest + playwright test
test_file = example_tests / "test_homepage.py"
test_file.write_text("""
import os
def test_dummy():
    assert 1 == 1
""", encoding="utf-8")

# run runner
res = run_playwright_tests("local-test-run", str(example_tests), headed=False)
print("Runner result:", res)