---
name: ship
description: Ship a branch — fix quality failures, merge to main, and delete the branch. Use when the user asks to ship or merge a branch.
---

You are tasked with shipping the branch. Determine the target branch from the user's input or the conversation history.

Follow these steps precisely:

1. **Checkout and Sync:**
   - Fetch all branches: `git fetch origin`
   - Checkout the branch: `git checkout <branch_name>`
   - Ensure it's up to date: `git pull origin <branch_name>`

2. **Fix Quality and CI Failures:**
   - Run the Python quality gate: `make quality-py`.
   - If it fails due to formatting, fix it: `make fmt-py`.
   - Run all tests: `make check`.
   - Verify everything is clean: `make precommit SKIP=1`.
   - If changes were made, commit them: `git commit -am "style: fix quality gate failures"`.

3. **Merge into Main:**
   - Switch to main: `git checkout main`
   - Pull latest: `git pull origin main`
   - Merge the branch: `git merge <branch_name>`
   - **Conflict Resolution:** If conflicts occur:
     - List conflicted files: `git status`.
     - Read and resolve each conflict manually or using tools.
     - Add resolved files: `git add <file>`.
     - Complete the merge: `git commit`.

4. **Final Verification:**
   - Run `make precommit SKIP=1` on the merged `main` branch to ensure no regressions.

5. **Cleanup:**
   - **Ask for acknowledgement before pushing changes.** (List the file names that will be committed/pushed).
   - Push main: `git push origin main`.
   - Delete the local branch: `git branch -d <branch_name>`.
   - Delete the remote branch: `git push origin --delete <branch_name>`.

6. **Report:**
   - Summarize the actions taken, including any conflicts resolved.
