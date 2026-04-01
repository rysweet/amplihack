# Workflow Worktree Isolation

**Stream-local worktrees, validated handoff, and local-src launcher bootstrapping for recipe-driven workflow runs.**

> [Home](index.md) > Workflow Worktree Isolation
>
> **Implemented in issue #4022 and preserved by issue #4077's recovery-stack consolidation:** this page documents the shipped contract that keeps post-step-04 workflow execution rooted in a stream-local worktree instead of drifting back to the shared checkout.

## Quick Navigation

- [Branch Name Generation](features/branch-name-generation.md)
- [Resumable Workstream Timeouts](features/resumable-workstream-timeouts.md)
- [Workflow Publish Import Validation](features/workflow-publish-import-validation.md)

---

## What This Feature Does

Workflow worktree isolation keeps every stream of a recipe-driven run inside its own validated checkout.

1. **Step 04 creates or reuses the branch worktree.** `default-workflow` derives a branch name from the task, creates or reuses `<repo>/worktrees/<branch>`, and emits `worktree_setup.worktree_path` plus `branch_name`.
2. **Step 04b validates the handoff immediately.** The workflow confirms that the directory exists, is the git top-level for that worktree, and is checked out on the expected branch before downstream agents run.
3. **Post-step-04 agents stay in the worktree.** Architecture, implementation, review, testing, checkpoint, and final-status steps treat `{{worktree_setup.worktree_path}}` as the active repository root rather than dropping back to `{{repo_path}}`.
4. **Step 15 publishes from the same validated checkout.** Commit/push revalidates the worktree path and branch before running scoped publish import validation and before creating a commit.
5. **Multitask launchers import from the stream-local source tree first.** Generated `launcher.py` files prepend the cloned workstream's `src/` tree before importing `amplihack.recipes`, so stale installed packages or shared-checkout `PYTHONPATH` contamination cannot hijack a stream.

This contract also preserves the clean-worktree invariant and validated branch handoff tightened in the related fixes tracked as issues #3673 and #3684.

---

## Operational Guarantees

| Guarantee                       | Behavior                                                                                                                                                | Why it matters                                                                                                               |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Stream-local execution root     | Every agent step after Step 04 uses `working_dir={{worktree_setup.worktree_path}}` and names that path as the active repository root.                   | Concurrent streams do not read from or write to the shared checkout by accident.                                             |
| No silent fallback              | Post-step-04 workflow commands and prompts do not drop back to `{{repo_path}}`.                                                                         | Shared-checkout contamination is treated as a bug, not a normal recovery path.                                               |
| Immediate worktree validation   | `step-04b-validate-worktree` checks directory existence, git membership, top-level path, and branch match.                                              | The workflow fails before design or implementation if setup drifted.                                                         |
| Publish-time revalidation       | `step-15-commit-push` rechecks the worktree path and current branch before staging, scoped import validation, and commit creation.                      | Publish-time safety stays aligned with the checkout that implementation used.                                                |
| Stream-local launcher bootstrap | Multitask launchers prepend the local workstream `src/` tree before importing `amplihack.recipes`, and pass durable worktree metadata into nested runs. | Resumed or parallel workstreams keep executing against their own clone rather than a stale installed package or shared tree. |

---

## Where the Contract Applies

| Surface                               | Contract                                                                                                                                       |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `default-workflow` Step 04 / Step 04b | Create or reuse the worktree, then validate that it is the real git root for the expected branch.                                              |
| Post-step-04 agent steps              | Use the worktree path as `working_dir` and reference it explicitly in prompts.                                                                 |
| `step-15-commit-push` and checkpoints | Revalidate the checkout, fail on branch drift, and refuse hollow-success publishes with no staged worktree changes.                            |
| Multitask `launcher.py` / `run.sh`    | Bootstrap imports from the local `src/` tree, propagate worktree/state/progress metadata, and keep resume context attached to the same stream. |

---

## What Happens When Something Is Wrong

The contract fails closed when:

- the worktree directory is missing
- the directory is not actually inside a git worktree
- the git top-level does not match the expected worktree path
- the current branch does not match the expected branch
- Step 15 finds no staged changes in the validated worktree and detects a hollow-success publish

The workflow should not respond to those failures by silently changing directories, silently reusing `repo_path`, or accepting shared-checkout imports as "good enough."

---

## Relationship to Related Workflow Features

- **Resumable Workstream Timeouts** preserve and later reuse the same worktree path, which is why timeout recovery can continue from a durable checkpoint without reconstructing a new checkout.
- **Workflow Publish Import Validation** runs inside the same validated worktree and branch that produced the implementation, so scoped publish validation and commit creation operate on the correct checkout.

If the worktree cannot be trusted, both of those higher-level features should stop rather than continue on a weaker assumption.

---

## Compatibility Note for Older Power Steering Links

This page is the canonical workflow-level overview. Earlier documentation also used a separate page for Power Steering-specific worktree behavior, and that legacy content still lives here:

- [Legacy Power Steering Worktree Support](features/power-steering/worktree-support.md)

---

## Where To Go Next

- Use [Branch Name Generation](features/branch-name-generation.md) to understand how Step 04 derives the stream-local branch and worktree names before validation starts.
- Use [Resumable Workstream Timeouts](features/resumable-workstream-timeouts.md) to understand preserved worktree reuse across timeouts and resume.
- Use [Workflow Publish Import Validation](features/workflow-publish-import-validation.md) to understand the Step-15 publish surface that runs inside the validated worktree.
