# Contributing — Team 4

Guidelines for contributing to this repository during **GDGoC Summer DevSprint 2026** (Aug 12–14, 2026).

## Getting Started

1. Clone the repo:
   ```bash
   git clone https://github.com/<org>/team-4.git
   cd team-4
   ```
2. Confirm you have push access under the `dev4` team. If not, ping a team lead or organizer.
3. Set up the project locally per the instructions in `README.md`.

## Branching

- `main` — stable, always demo-ready. Do not push directly.
- `dev` — active integration branch.
- `feature/<short-name>` — one branch per feature/task (e.g. `feature/auth-flow`).

Open a pull request from your feature branch into `dev`. Merge `dev` → `main` only at agreed checkpoints (end of Day 1, Day 2, and before final submission).

## Commit Messages

Use short, present-tense messages:
```
add login form validation
fix mongo connection timeout
update README with setup steps
```

## Pull Requests

- Keep PRs small and scoped to one feature/fix.
- At least one other teammate should review before merging into `dev`.
- Resolve merge conflicts locally before requesting review.
- Reference the relevant task/issue in the PR description if using GitHub Issues/Project board.

## Code Style

- Match the formatting/linting already configured in the repo (see `README.md` for tooling).
- Comment non-obvious logic, especially around sponsor API integrations (e.g. MongoDB, Google Cloud).
- Do not commit `.env` files, API keys, or credentials — use `.env.example` for placeholders and ensure `.env` is in `.gitignore`.

## Issues

Use GitHub Issues to track tasks and bugs. Label by type (`feature`, `bug`, `docs`) and priority if helpful for the 3-day sprint.

## Submission Checklist (before Devpost/Devfolio deadline)

- [ ] `main` branch builds/runs cleanly
- [ ] `README.md` updated with setup + demo instructions
- [ ] Team members and roles listed in `README.md`
- [ ] Sponsor tech usage documented (if applicable)
- [ ] Devpost/Devfolio submission links to this repository

## Questions

For sprint logistics or access issues, contact the GDGoC Summer DevSprint 2026 organizing committee.
