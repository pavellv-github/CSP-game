# Game Git Workflow

> Источник правды по веткам, версиям, релизам и правилам для ИИ-агентов (инструкция владельца, 2026-10-18). Заменяет прежнюю модель `docs/BRANCHING.md` (релизные ветки по мажорам); проектные дополнения — в `docs/BRANCHING.md`.

## 1. Purpose

This document defines the Git branching strategy, versioning rules, release process, and requirements for AI coding agents working on the game.

The goals are:
- Maintain a stable and buildable `main` branch.
- Develop features and fixes independently.
- Integrate changes safely.
- Prepare releases without blocking ongoing development.
- Track every released version and its corresponding build.
- Prevent unauthorized Git operations and releases.

## 2. Branching Strategy

Use the following branches:

| Branch | Purpose | Lifetime |
|---|---|---|
| `main` | Stable, integrated game development branch | Permanent |
| `feature/*` | New gameplay mechanics and functionality | Temporary |
| `fix/*` | Bug fixes not requiring a release hotfix | Temporary |
| `release/*` | Release stabilization | Until release completion |
| `hotfix/*` | Urgent fixes for released versions | Temporary |

Examples:

- `feature/inventory-system`
- `feature/quest-system`
- `fix/inventory-duplication`
- `release/0.3.0`
- `hotfix/save-corruption`

Do not create a permanent `develop` branch unless the project demonstrates a concrete need for it.

### 2.1. Main Branch

`main` is the primary integration branch.

Requirements:
- The game must remain buildable.
- Existing functionality must not be broken by integrations.
- Changes must be reviewed and tested before merging.
- Incomplete features must not disrupt existing gameplay.
- Releases must be created from an explicitly approved state of `main`.

The latest commit on `main` is not necessarily the latest released version.

### 2.2. Feature Branches

Create a separate branch for each feature.

Branch from the latest appropriate `main` commit:

    git switch main
    git pull --ff-only
    git switch -c feature/feature-name

Rules:
- Keep each branch focused on one logical task.
- Avoid mixing unrelated changes.
- Commit changes in logical units.
- Keep the branch synchronized with `main` when necessary.
- Submit a pull request when implementation and required checks are complete.
- Delete the branch only after its changes have been integrated and deletion is authorized.

### 2.3. Fix Branches

Use `fix/*` for ordinary bug fixes.

Example:

    git switch main
    git pull --ff-only
    git switch -c fix/bug-description

If the bug affects a released version and requires an urgent patch, use `hotfix/*` instead.

## 3. Pull Requests and Integration

All feature and fix branches should be integrated through pull requests when the repository platform supports them.

Before merging, verify:

1. The change satisfies the task requirements.
2. The project builds successfully.
3. Relevant automated tests pass.
4. The game starts and the affected mechanics work.
5. No unrelated files or changes are included.
6. No secrets, credentials, or local configuration files are committed.
7. Merge conflicts have been resolved correctly.

If automated tests are unavailable, perform the applicable manual checks and report the limitations.

Do not claim that a build or test passed unless it was actually executed and its result verified.

### Integration rules

- Do not merge incomplete or unverified work into `main`.
- Do not bypass required repository checks.
- Do not overwrite another developer's work.
- Do not silently discard changes while resolving conflicts.
- Do not use force-push to resolve integration problems.

After integration, remove temporary branches only when authorized.

## 4. Release Versioning

Use Semantic Versioning:

    MAJOR.MINOR.PATCH

Examples:

- `0.1.0` — initial prototype release.
- `0.2.0` — new gameplay functionality.
- `0.2.1` — bug fixes.
- `1.0.0` — first stable release.
- `1.1.0` — new functionality in a stable release.
- `1.1.1` — bug fixes for the stable release.

During early development, use `0.x.y` versions.

Version increments:

| Component | When to increment |
|---|---|
| MAJOR | Major release or breaking changes according to project policy |
| MINOR | New functionality or significant gameplay changes |
| PATCH | Bug fixes and compatible corrections |

The exact meaning of a version increment should reflect the project's release policy.

Do not change the release version arbitrarily. Confirm the target version before preparing a release.

## 5. Release Workflow

A release begins when the planned feature set has been integrated into `main` and the project is ready for stabilization.

### Step 1. Define the release scope

Determine:
- Target version.
- Included features.
- Included bug fixes.
- Required testing.
- Known issues.
- Target platforms.
- Release criteria.

Do not create a release branch before the release scope has been agreed upon.

### Step 2. Verify main

Inspect the repository state:

    git status
    git branch --show-current
    git log --oneline -10

Verify that:
- The working tree is clean.
- The correct branch is checked out.
- The intended changes are integrated.
- The project builds successfully.
- The release scope is satisfied.

### Step 3. Create the release branch

Example for version `0.3.0`:

    git switch main
    git pull --ff-only
    git switch -c release/0.3.0

Creating this branch is a release preparation action and requires explicit authorization.

### Step 4. Stabilize the release

The release branch is intended primarily for:
- Bug fixes.
- Balance adjustments.
- Performance corrections.
- Build configuration changes.
- Release metadata updates.
- Other changes necessary to meet release criteria.

Do not add unrelated major features to an existing release branch.

Every change must be reviewed and tested.

### Step 5. Prepare the release candidate

Build and test the game on the intended platforms.

If release candidates are needed, use prerelease identifiers such as:

    0.3.0-rc.1
    0.3.0-rc.2

Do not mark a release candidate as a final release.

### Step 6. Create the release tag

After final approval, create an annotated Git tag on the exact commit being released:

    git tag -a v0.3.0 -m "Release 0.3.0"

Verify the tag:

    git show v0.3.0

Pushing the tag requires explicit authorization:

    git push origin v0.3.0

The tag must point to the commit corresponding to the released build.

Never move or overwrite an existing release tag without explicit authorization.

### Step 7. Build and publish

Build the game from the approved release commit.

Record:
- Game version.
- Build number.
- Git commit hash.
- Target platform.
- Build configuration.
- Build date.
- Release status.

Publishing, uploading builds, or distributing the game requires explicit authorization.

### Step 8. Synchronize release fixes

Fixes introduced on the release branch must also reach `main`.

After the release is complete, integrate the release branch into `main` when appropriate:

    git switch main
    git merge release/0.3.0

Inspect the result and resolve conflicts without discarding unrelated changes.

If merging the entire release branch is inappropriate, transfer the required fixes individually using an approved strategy, such as `cherry-pick`.

Verify that the fixes are present in `main`.

### Step 9. Close the release

After verification:
- Confirm the release tag points to the correct commit.
- Confirm release fixes are present in `main`.
- Record the release notes.
- Archive release metadata.
- Delete temporary branches only when authorized.

## 6. Hotfix Workflow

A hotfix is an urgent correction to an already released version.

Example: the game has released version `0.3.0`, and a critical save corruption bug is discovered.

Create the hotfix branch from the released tag:

    git switch -c hotfix/save-corruption v0.3.0

Implement the smallest safe correction.

Run relevant tests and build checks.

Prepare version `0.3.1` and obtain release approval.

Tag the approved commit:

    git tag -a v0.3.1 -m "Release 0.3.1"

Publish only after explicit authorization.

Then ensure the fix is incorporated into `main`.

Do not assume that fixing the latest `main` automatically fixes an older released version.

If multiple supported release lines exist, determine which versions require the fix.

## 7. Build Identification

A release should be identifiable independently of its file name.

Record at least:

    GAME_VERSION=0.3.0
    BUILD_NUMBER=184
    GIT_COMMIT=a1b2c3d

These values are illustrative.

Requirements:
- `GAME_VERSION` identifies the game release.
- `BUILD_NUMBER` identifies a particular build.
- `GIT_COMMIT` identifies the source revision.
- Build numbers must follow a consistent project-wide policy.
- Released build metadata must not be silently rewritten.
- Do not invent build numbers or commit hashes.

If the engine or build system has its own versioning mechanism, use it consistently rather than introducing unnecessary parallel configuration.

The exact implementation depends on the game's engine and existing build pipeline.

## 8. Commit Conventions

Use descriptive commit messages.

Recommended format:

    type(scope): description

Examples:

    feat(inventory): add item stacking
    fix(save): prevent corrupted save data
    perf(combat): reduce collision checks
    refactor(quests): simplify quest state handling
    test(inventory): cover item transfer
    docs(release): update release checklist

Recommended types:
- `feat` — new functionality.
- `fix` — bug fix.
- `perf` — performance improvement.
- `refactor` — internal restructuring.
- `test` — tests.
- `docs` — documentation.
- `build` — build system and configuration.

Do not create commits containing unrelated changes merely to reduce the number of commits.

## 9. Rules for AI Coding Agents

The coding agent must follow these rules in every repository session.

### 9.1. Before making changes

Inspect the repository:

    git status
    git branch --show-current
    git log --oneline -10

Determine:
- Current branch.
- Working tree state.
- Existing uncommitted changes.
- Relevant recent commits.
- Applicable repository instructions.
- Available build and test commands.

Never assume the repository is clean.

Never overwrite user changes.

### 9.2. During development

- Work only on the requested task.
- Use the appropriate feature or fix branch.
- Follow existing project conventions.
- Avoid unrelated refactoring.
- Run relevant tests and checks.
- Report failures and limitations honestly.
- Do not modify release metadata without a task-specific reason.

### 9.3. Before integration

Provide a concise summary of:
- Files changed.
- Functionality implemented.
- Tests and builds executed.
- Test results.
- Known limitations.
- Current branch and working tree state.

Do not claim that changes have been integrated unless the merge actually occurred.

### 9.4. Operations requiring explicit authorization

Unless the user explicitly authorizes the operation, do not:

- Merge changes into `main`.
- Push commits or branches to a remote repository.
- Force-push.
- Execute `git reset --hard`.
- Delete branches or tags.
- Rewrite published Git history.
- Overwrite existing release tags.
- Create or publish an official release.
- Upload or distribute a game build.
- Deploy to production or submit a build to an app store.
- Discard uncommitted user changes.

Before any destructive operation, explain what will change and obtain confirmation.

A general request to implement a feature does not authorize a release or publication.

### 9.5. When encountering conflicts

- Inspect both sides of the conflict.
- Preserve unrelated changes.
- Avoid automatic resolution when the intended behavior is unclear.
- Explain the conflict and request clarification when necessary.
- Never discard changes simply to make a merge succeed.

### 9.6. Final report

After completing a task, report:

1. Summary of changes.
2. Branch used.
3. Commits created, if any.
4. Tests and build checks performed.
5. Results and known limitations.
6. Whether changes remain uncommitted.
7. Whether a merge, push, release, or publication is still pending.

Do not state that an action was completed if it was not executed.

## 10. Standard Development Cycle

The expected development cycle is:

    Task
      |
      v
    Create feature/fix branch
      |
      v
    Implement changes
      |
      v
    Run tests and build checks
      |
      v
    Review changes
      |
      v
    Pull request
      |
      v
    Approved integration into main
      |
      v
    Repeat until release scope is complete
      |
      v
    Create release branch
      |
      v
    Stabilize and test
      |
      v
    Approve release
      |
      v
    Tag exact release commit
      |
      v
    Build and publish
      |
      v
    Synchronize fixes into main

## 11. Core Principles

1. `main` is the stable integration branch, not a guarantee that every commit is released.
2. Features are developed independently.
3. A release branch is created only after the release scope is defined.
4. Release branches prioritize stabilization over new functionality.
5. Every official release has a unique version tag.
6. Every distributed build must be traceable to a source commit.
7. Fixes made during release preparation must not be lost from future development.
8. Hotfixes start from the affected released version.
9. Tests and build results must be reported accurately.
10. The coding agent must not perform destructive Git operations, integrate into `main`, push, publish, or distribute builds without explicit authorization.
