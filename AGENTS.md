# AGENTS.md

## Mission Statement

This project exists to provide a reliable, maintainable ComfyUI plugin for Midjourney workflows.
Engineering priority is behavior safety, clean refactors, strong observability, and long-term maintainability.

## Purpose

- This file defines engineering guardrails for this repository.
- Keep this file focused on code quality, maintainability, observability, safety, and verification.
- Do not use this file for feature specs or product planning.

## Environment and Command Execution

- Use the Python environment that hosts this ComfyUI instance

## Core Engineering Principles

- Write self-documenting code with expressive, concise names.
- Favor DRY when it reduces repeated change risk.
- Do not force DRY when abstraction harms clarity.
- Keep separation of concerns strong and obvious.
- Keep modules cohesive and responsibilities narrow.
- Place new code deliberately where it naturally belongs.
- Do not place code opportunistically "where it works".
- Refactors must be complete: update callsites, remove dead code, and remove temporary bridges.
- Prefer clean replacement over preserving outdated internal structures.

## Behavior Safety

- Preserve current ComfyUI-facing behavior unless the change is explicitly intentional.
- Treat prompt construction, task submission, polling, image handling, and node outputs as behavior-critical paths.
- Before refactoring behavior-heavy areas, add characterization or regression tests for the current behavior.
- If behavior changes intentionally, call it out explicitly and verify the new behavior with tests.

## Code Organization and Readability

- Avoid god files and mixed responsibilities.
- Shared logic should live in shared modules instead of being duplicated across node implementations.
- Keep public entrypoints thin and move reusable logic into focused helpers or service modules when it improves clarity.
- Remove obsolete paths when replacements are complete.

## Mutiny Integration Boundary

- `mutiny` is the backend boundary for this repository.
- Local Mutiny source checkout: `E:\devprojects\mutiny`.
- Future distribution name: `mutiny-sdk`.
- Python import package: `mutiny`.
- Integrate through Mutiny's documented public API surface only.
- Treat package-root exports from `mutiny` plus a host-side `TokenProvider` as the supported integration contract.
- Supported host-facing Mutiny symbols include `Mutiny`, `Config`, `JobHandle`, `JobSnapshot`, `ProgressUpdate`, `JobStatus`, `ImageResolution`, `VideoResolution`, `ImageTile`, `ImageOutput`, `VideoOutput`, and `TextOutput`.
- Do not treat `mutiny.types` as the supported host contract for this plugin.
- Removed or unsupported facade methods such as `change`, `custom_zoom`, `inpaint`, `find_job_by_image`, and `expand_tiles` are not allowed in new plugin code.
- Do not import or depend on `mutiny` package internals from this repository unless a maintainer explicitly approves it.
- If the public API is missing something needed here, add the capability to Mutiny or add a local adapter around the public surface instead of reaching into internals.

## Docstrings and Comments

- Docstrings are mandatory for all new and changed modules, classes, functions, and non-trivial methods.
- Use concise imperative docstrings for simple logic.
- Use Google-style docstrings for complex logic.
- Docstrings must explain intent, constraints, and rationale, not restate obvious mechanics.
- Inline comments are allowed only for non-obvious behavior, invariants, edge cases, or external constraints.

## Documentation Policy

- Do not create extra docs files unless explicitly requested.
- Required context should live in code, tests, docstrings, and concise inline comments where justified.
- English documentation is the source of truth unless a maintainer explicitly approves otherwise.
- User-facing docs that exist in both English and Chinese must stay aligned in meaning.
- When changing English README or docs content, update the matching Chinese docs in the same change unless a maintainer explicitly approves a deferment.
- Do not leave known English/Chinese doc drift uncalled out.
- When reporting completion for docs changes, state whether the Chinese counterpart was updated or confirm that no Chinese counterpart exists.

## Observability

- Observability is mandatory.
- Use module-level `logging` loggers for runtime diagnostics.
- Do not use `print` for runtime diagnostics.
- Logs must be actionable and include the context needed to diagnose failures quickly.
- Include relevant identifiers and state where available, such as node/action name, task ID, model/version, proxy operation, retry state, timeout state, and config source.
- Preserve exception context and stack traces for unexpected failures.
- Do not swallow exceptions silently.
- Bare `except:` is not allowed.
- Broad `except Exception` blocks are allowed only at intentional plugin boundaries and must log useful context before returning a user-safe error.
- Current dev-mode note: plugin-built Mutiny configs force gateway/response capture on for diagnostics.
- When investigating hangs, misclassified MJ messages, missing previews, or other runtime issues, inspect `.cache/mutiny/mj_responses/` first for `gw_*.json`, per-message dumps, and `index.jsonl`.
- Treat that capture path as temporary developer forensics, not a user-facing feature flag, and do not silently remove or disable it while debugging related failures.

## Secrets and Sensitive Data

- Never commit or log secrets, tokens, credentials, or private configuration values.
- Keep logs free of sensitive prompt content unless the exact content is required for diagnosis.
- When logging paths or config sources, include only the minimum detail needed to debug the issue.

## Safety Rules

- Treat configuration loading, proxy startup, subprocess execution, and network calls as safety-sensitive.
- Validate external paths and configuration values before using them.
- Use subprocess argument lists, never shell-string execution.
- Network operations must use explicit timeouts.
- Fail clearly when required configuration is missing or invalid.

## Testing Policy

- Add or update tests for every behavior change and bug fix.
- Add characterization tests before refactoring behavior-critical flows.
- Cover both success and failure paths.
- Keep tests deterministic and isolated.
- Prefer real behavior tests over excessive mocking.
- Mock only true external boundaries such as network calls, subprocesses, and host-specific ComfyUI surfaces.
- Failing tests are blocking.

## Python Toolchain

- Formatter: `ruff format`
- Linter: `ruff check`
- Test runner: `pytest`

## JavaScript Toolchain

- This section applies only if JavaScript is added to the repository.
- Formatter: `prettier`
- Linter: `eslint`
- Test runner: `vitest` for non-trivial JavaScript logic.
- Add or update JavaScript tests for every JavaScript behavior change.
- Do not add JavaScript tooling without wiring its verification commands into the repo workflow.

## Verification Workflow

- Run focused checks while implementing.
- Run all relevant quality gates before reporting completion.
- Do not report completion if blocking checks fail.
- If a relevant automated check cannot run, state that explicitly along with the remaining risk.

## Definition of Done

- Behavior is preserved or intentionally changed and verified.
- New and changed code follows the repository's organization and separation-of-concerns rules.
- Required docstrings are present and meaningful.
- Logging and error handling are actionable.
- Relevant Chinese documentation is updated when corresponding English user-facing documentation changes, or any intentional gap is explicitly called out.
- Relevant format, lint, and test checks pass.

## Commit Policy

- Use Conventional Commits: `type(scope): subject`.
- Allowed types: `feat`, `fix`, `refactor`, `test`, `chore`, `docs`, `build`, `ci`.
- Keep commits atomic and cohesive.

## Maintainer Authority

- Maintainer instructions override this file.
- If constraints conflict, pause and ask for maintainer direction.
