# Frontend Machine Agent Rules

本文件定义前端电脑的本机角色。前端电脑必须同时遵守 `docs/TWO_MACHINE_COLLABORATION_PROTOCOL.md`。

## Role

This machine follows the frontend-machine role unless the user explicitly authorizes backend changes.

## Allowed Work

- Develop frontend code.
- Develop frontend tests.
- Maintain frontend build scripts.
- Configure frontend/backend integration for local verification.
- Start or configure local backend services for integration verification.

## Forbidden Without Explicit User Authorization

- Do not modify backend application code.
- Do not modify database schema or migrations.
- Do not implement backend features.
- Do not change backend API behavior.

## Completion Rules

- Update related specs, plans, contracts, or roadmap TODO state in the same change set.
- After local frontend verification passes, commit and push to remote `main`.
- If backend changes are required, stop and ask the user to route the work to the backend machine or explicitly authorize the exception.
