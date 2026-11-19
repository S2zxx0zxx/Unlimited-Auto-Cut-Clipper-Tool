# Contributing

Contributions are welcome for authorized-stream recording, playback compatibility, media resilience, detection quality and accessibility.

- Open a focused issue before major architecture changes.
- Keep new features fully local by default, and document any new network access explicitly.
- Add reproducible synthetic tests for extraction, scoring and recovery changes; don't add copyrighted clips.
- Run `python -m compileall -q src tests` and `python -m unittest discover -s tests -p 'test_*.py' -v` before proposing a PR.
- Report security vulnerabilities privately where possible rather than posting exploit details in public issues.
- By contributing, you agree that contributions are distributed under GPL-3.0-only, the repository license.
