# Contributing to Satoshi API

Thanks for your interest in contributing!

## Reporting Bugs

Open an issue using the bug report template. Include:
- Steps to reproduce
- Expected vs actual behavior
- Your environment (Python version, Bitcoin Core version, OS)

## Security Issues

**Do not open a public issue for security vulnerabilities.** See [SECURITY.md](SECURITY.md) for how to report them privately.

## Development Setup

```bash
git clone https://github.com/Bortlesboat/bitcoin-api.git
cd bitcoin-api
pip install -e ".[dev]"
```

You'll need a Bitcoin Core node running with `server=1` for e2e tests. Unit tests mock the RPC connection and don't require a node.

## Running Tests

```bash
# Unit tests (no node required)
python -m pytest tests/test_api.py -q

# E2E tests (requires running node + API)
python -m pytest tests/test_e2e.py -m e2e

# Load test
locust -f tests/locustfile.py --host http://localhost:9332
```

## Pull Requests

1. Fork the repo and create a branch from `master`
2. Add tests for any new endpoints or behavior changes
3. Run `python -m pytest tests/test_api.py` and ensure all tests pass
4. Keep PRs focused — one feature or fix per PR
5. Update `docs/SCOPE_OF_WORK.md` if you add/change endpoints

## Code Style

- Follow existing patterns in the codebase
- Use type hints for function signatures
- Response envelope: `{ data, meta }` on success, `{ error }` on failure
- All endpoints under `/api/v1/`
- Input validation before RPC calls

## Adding a New Endpoint

1. Create or extend a router in `src/bitcoin_api/routers/`
2. Follow the existing response envelope pattern
3. Add unit tests in `tests/test_api.py`
4. Update the endpoint table in `README.md`
5. Update `docs/SCOPE_OF_WORK.md` Section 3

## Developer Certificate of Origin (DCO)

This project uses the [Developer Certificate of Origin](https://developercertificate.org/) (DCO). All contributions must include a `Signed-off-by` line in the commit message, certifying that you wrote or have the right to submit the code under the project's license.

### How to sign off

Add `-s` to your git commit command:

```bash
git commit -s -m "Add new endpoint for X"
```

This adds a line like:

```
Signed-off-by: Your Name <your@email.com>
```

If you forgot to sign off on a commit, you can amend it:

```bash
git commit --amend -s
```

### What the DCO means

By signing off, you certify (per [developercertificate.org](https://developercertificate.org/)):

1. You created the contribution, or have the right to submit it.
2. You understand it will be public and a record of the contribution is maintained.
3. You license the contribution under the project's Apache 2.0 license.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
