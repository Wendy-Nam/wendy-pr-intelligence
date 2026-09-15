# Public briefing samples

Run from the repository root after installing `requirements.txt`:

```bash
python scripts/demo/build_samples.py
```

The builder uses the production HTML renderers with fictional, fixed news fixtures.
Network collection and LLM calls are replaced with local fixtures; no email is sent.
Configuration and intermediate outputs live in a temporary directory. Only public
HTML and sample JSON are written to `docs/demo/`. The landing page is maintained
in `docs/demo/index.html`.

GitHub Actions publishes **only `docs/demo/`** when these files change on main.
Enable the repository's Pages source as GitHub Actions. Architecture reports,
real company configuration, credentials, and runtime outputs are not site assets.
