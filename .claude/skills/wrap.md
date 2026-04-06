---
name: wrap
description: End-of-session wrap-up — commits, pushes, updates context files, and saves memory for next session
user_invocable: true
---

# Session Wrap-Up

Perform ALL of the following steps in order. Do not skip any step.

## 1. Check for uncommitted changes
Run `git status` in the project root. If there are staged or unstaged changes:
- Stage all relevant files (exclude `.env`, `data/cache/`, `__pycache__/`)
- Create a descriptive commit summarizing what was done this session
- Push to remote

If there are no changes, skip to step 2.

## 2. Update CLAUDE.md
Read the current `CLAUDE.md`. If any of the following changed this session, update it:
- Project structure (new files/folders added)
- Tech stack changes
- Key decisions or architecture changes
- Build phase progress (mark completed phases, note what's next)

If nothing changed, skip to step 3.

## 3. Update ROADMAP.md
Read the current `ROADMAP.md`. Check off any tasks that were completed this session using `[x]`. If new tasks were identified, add them.

## 4. Save memory for next session
Update the memory files at the project memory directory:
- Update `project_status.md` with current phase, what was done, and what's next
- Update `user_context.md` if any new user preferences or context were learned
- Add new memory files if significant decisions or feedback were given this session
- Update `MEMORY.md` index if any memory files were added

## 5. Commit context updates
If steps 2-4 produced any file changes:
- Stage the updated files
- Commit with message: "Update project context for next session"
- Push to remote

## 6. Final status
Tell the user:
- What was committed and pushed
- What the current project state is
- What to work on next session
- Confirm everything is saved and they're good to go
