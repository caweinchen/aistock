# Expo HAS CHANGED

Read the exact versioned docs at https://docs.expo.dev/versions/v56.0.0/ before writing any code.

# Communication

Use Chinese for assistant responses by default unless the user explicitly asks for another language.

# Documentation and Planning

All planning and roadmap documents must use explicit `TODO` tracking for unfinished work. When a task, phase, or sub-slice is completed, update the corresponding document in the same change set to mark it as completed or partially completed, so later follow-up work can rely on the document state.

Use structured design for specs and plans. Keep each document focused and reasonably small; split large work into multiple design documents or implementation plans instead of letting a single document grow too large.

# Two-Machine Collaboration

Both development machines must follow `docs/TWO_MACHINE_COLLABORATION_PROTOCOL.md`.

This machine follows the frontend-machine role defined in `docs/agents/frontend-machine.md`.

# Git Remotes

Gitee is the primary Git remote and must be named `gitee`. GitHub is the secondary mirror and must remain named `origin`.

- Local `main` must track `gitee/main`.
- Before work, fetch or pull from `gitee/main` first. Preserve and integrate concurrent remote work; never overwrite it silently.
- After a verified commit, push `main` to `gitee` first, then push the same commit to GitHub `origin`.
- Work is not considered remotely synchronized unless the Gitee push succeeds and its remote SHA is verified.
- If GitHub cannot be reached, report the exact failure, leave an explicit TODO to retry, and do not describe GitHub as synchronized.
- Never force-push any branch unless the user explicitly authorizes that specific force-push after reviewing the remote divergence.
- Multica agents must prefer the Gitee repository resource. Do not fall back to GitHub merely to bypass a Gitee error without reporting it.
