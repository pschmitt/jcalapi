# Agent instructions

`jcalapi` provides a JSON API backed by local calendar caching. Preserve its API responses and cache behavior when changing request handling or calendar parsing.

## Working and validation

- Follow the README and `pyproject.toml` for setup and configured checks.
- Add or update focused tests for API and caching changes; use local fixtures rather than live calendar services.
- Before changing GitHub Actions, check whether [pschmitt/ci-workflows](https://github.com/pschmitt/ci-workflows) provides a reusable workflow or action. Preserve current behavior and check coverage, and use `@main` for shared workflow or action references.
