# Contributing

## Ways to Help

- **Add an example** — run the framework for your company and add the
  generated files under `examples/your-company/`
- **Fix a bug** — open an issue describing what went wrong
- **Improve the wizard** — `wizard.py` handles the non-technical setup
- **Add a language** — translate `wizard.py` prompts for non-English users
- **Test on Windows** — most testing has been on Mac/Linux

## How to Submit

1. Fork the repo
2. Create a branch: `git checkout -b fix/what-you-fixed`
3. Make your change
4. Test it: run `python wizard.py` end-to-end
5. Open a pull request with a short description

## Security Issues

Do NOT open a public issue for security vulnerabilities.
Use GitHub's private security advisory instead.

## What Not to Contribute

- Do not commit `.env` files or credentials
- Do not commit lead CSVs or reply logs (they contain personal data)
- Do not add paid API dependencies — the free stack is a core principle
