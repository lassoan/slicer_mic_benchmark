# Instructions for AI agents

- **Running the benchmark** and adding a run's findings: follow
  [.claude/skills/run-benchmark/SKILL.md](.claude/skills/run-benchmark/SKILL.md).
- **Manual for humans:** [RUNNING.md](RUNNING.md).

Rules that always apply:

- Never add CPU load while a benchmark run is in progress. Check the run's log in `results/<run>/run-*.log`.
- Published files must not contain personal information: user name, computer name, absolute paths, or names of
  running programs. `python scripts/check_privacy.py` checks this.
- Don't commit `.envs/`, `data/`, `wheels/`, `reports/` or `site/`.
