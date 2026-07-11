# Backend Machine Agent Rules

本文件定义后端电脑的本机角色。后端电脑必须同时遵守 `docs/TWO_MACHINE_COLLABORATION_PROTOCOL.md`。

## Role

This machine follows the backend-machine role unless the user explicitly authorizes frontend changes.

## Allowed Work

- Develop backend code.
- Develop database migrations and backend data model changes.
- Develop backend tests.
- Maintain API contract documents.
- Configure backend services for local verification and frontend integration.

## Forbidden Without Explicit User Authorization

- Do not modify frontend application code.
- Do not implement frontend screens, components, hooks, or frontend services.
- Do not change frontend build behavior.

## API Contract Rules

- Any API, auth, error-code, response-field, or data-semantics change must update `docs/contracts/`.
- If frontend integration requires a behavior change, document the contract first, then implement the backend change.

## Completion Rules

- Update related specs, plans, contracts, or roadmap TODO state in the same change set.
- After local backend verification passes, commit and push to remote `main`.
- If frontend changes are required, stop and ask the user to route the work to the frontend machine or explicitly authorize the exception.
