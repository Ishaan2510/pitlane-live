# The test_*.py files next to this one are manual run-it-yourself scripts, not pytest tests.
# Ignoring them here makes `python -m pytest backend` (from the repo root) collect only tests/.
collect_ignore = ['test_fastf1.py', 'test_processed_data.py', 'test_race_scoring.py', 'test_token.py']
