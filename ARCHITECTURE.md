# Architecture Contract

Apply this contract to new Python code and refactors in this repository unless explicitly instructed otherwise.

## Project-Specific Companion
- This file is the shared base contract.
- A repository may add `ARCHITECTURE.project.md` for repository-specific rules.
- Read both files together when the project-specific file exists.
- If the two files conflict, `ARCHITECTURE.project.md` wins for that repository.
- Keep reusable rules here and move repository-specific variations to the project-specific file.

## 1. Design
- Prefer small, focused classes.
- Use inversion of control by default.
- Inject collaborators through constructors.
- Prefer composition over inheritance.

## 2. Dependencies
- Define injectable collaborator protocols in `src/protocols.py`, including `ILogger` for business logging.
- Depend on protocols instead of concrete implementations.
- `main.py` owns top-level wiring and configuration.
- Maintain `requirements.txt` for deployed runtime dependencies.
- Keep `requirements.txt` alphabetically ordered.
- Keep local-development-only dependencies in a separate development manifest.
- Add a short comment for every dependency entry describing what the library does and how the project uses it.
- Install both the runtime and development dependency manifests in development environments.
- Add new dependencies to the development manifest by default unless production runtime needs them.
- Work on the branch already checked out in the workspace unless the user asks to switch.

## 3. Null Safety
- Add runtime null guards for constructor arguments and public inputs that come from outside the class.
- If a value is null-guarded, annotate it with `| None`.
- Raise `ValueError` with clear messages such as `"<arg_name> must not be null"`.

## 4. Typing
- Fully type constructors, methods, returns, fields, constants, and important locals.
- Prefer precise types over `Any`.
- Use `Path` for filesystem paths.
- Keep the code free of type-checker warnings.

## 5. Module Responsibilities
- `main.py` owns CLI parsing, defaults, wiring, and bootstrap configuration.
- Business classes must not own CLI concerns.
- Keep environment-specific defaults near the entry point unless there is a strong reason not to.
- Avoid hidden global state.
- Do not create module names that conflict with the Python standard library.
- Do not introduce compatibility-layer or shim modules; refactor directly.

## 6. Error Handling
- Prefer defensive programming: validate assumptions early, guard invariants, and fail clearly.
- Prefer fail-fast programming: detect invalid state or invalid input as early as practical and stop immediately with a clear error.
- Validate early and fail clearly.
- Use deterministic errors for invalid arguments, files, and content.
- Handled errors must not emit a traceback.
- Log handled errors once at the CLI boundary.
- Preserve tracebacks for unhandled errors.
- Return sentinel values only when the feature contract explicitly requires them.

## 7. Testing
- Add or update tests for every behavior change.
- Use stubs or fakes for unit tests.
- Use real collaborators together in integration tests.
- Cover null guards, argument validation, happy paths, and failure paths.
- Type pytest fixtures where useful.

## 8. Diagrams and Generated Docs
- Update related PlantUML diagrams whenever behavior, structure, wiring, collaborators, or entrypoints change.
- Give every user-facing or externally triggered entrypoint its own sequence diagram.
- Update the class diagram when class structure changes.
- Remove or replace stale diagrams.
- Regenerate PNGs for every updated `.puml` in the same task and write each PNG next to its source.
- Use a local PlantUML renderer when available; otherwise use the official PlantUML server.
- Treat stale or missing diagram PNGs as an incomplete task state.
- Keep `README.md` generated and current.
- Use `docs/README_TEMPLATE.md` as the README structure.
- Keep mutable README narrative content in tagged Python docstrings or script comment blocks using `[README:<KEY>] ... [/README]`.
- Use class and method docstrings as source material for implementation-oriented README sections.
- Use `{{README:<KEY>}}` placeholders in `docs/README_TEMPLATE.md`.
- Generate `README.md` with `python scripts/generate_readme.py`.
- Ensure `README.md` includes:
  - an `Entrypoints` section covering every current user-facing or externally triggered entrypoint
  - a short behavior summary plus arguments, required flags, and defaults for each documented entrypoint
  - a link to `BUSINESS.md`
  - inline diagram PNGs plus links to their sources
- Keep `BUSINESS.md` focused on concrete business behavior, workflows, user-visible rules, and integration-facing behavior.
- Update `BUSINESS.md` when behavior changes.
- Avoid duplicating architecture-only rules in `BUSINESS.md`.

## 9. CLI
- Use `argparse`.
- Do not use `print()` for application output; use logging.
- Keep CLI parsing separate from domain logic.

## 10. Refactoring
- Preserve behavior unless the requested change explicitly changes behavior.
- When introducing IoC, update tests to match the new wiring.
- When adding null guards, update type signatures to match.

## 11. Style
- Store shared magic strings in `src/constants.py`.
- Store shared default values in `src/defaults.py`.
- Prefer named constants over repeated string literals.
- Use Pythonic style rather than Java-style ceremony.
- Prefer guard clauses and direct assignment over `if ... else` assignment blocks.
- Prefer direct construction over trivial constructor-only factory wrappers unless the wrapper adds real behavior or wiring.
- Do not add placeholder no-op `main()` functions to non-entrypoint modules.
- Keep implementations simple, readable, and explicit.
- Use ASCII unless the file already requires Unicode.
- Add concise comments where they clarify non-obvious logic or integration boundaries.
- Add a docstring to every class and every method.
- Class docstrings must describe the class purpose and briefly explain how it achieves that purpose.
- Method docstrings must describe the method purpose and briefly explain how it achieves its result, especially when coordinating collaborators, validating inputs, bridging sync/async work, or maintaining caches or locks.
- After source files are added, changed, renamed, or removed, review and update nearby docstrings and clarifying comments.
- Treat stale or missing docstrings and stale explanatory comments as defects.

## 12. Formatting
- After source files are added, changed, or removed, run `black .` from the repository root.
- Treat formatter output as part of the required final state.
- When adding a VS Code extension for the workspace, add it to `.devcontainer/devcontainer.json` under `customizations.vscode.extensions`.

## 13. Logging
- Use `trace`, `info`, `warning`, and `error` logging where appropriate.
- Use `@traced` from `autologging` on concrete application methods.
- Inject `ILogger` into business classes.
- Use one shared logger instance across the application.
- Integrate standard logging with Loguru through an intercept handler.
- Keep project-specific logging glue in a dedicated application logging module such as `src/app_logging.py`.
- Store the default Loguru configuration in a shared defaults module such as `src/defaults.py`.
- Load a filesystem override such as `config/loguru.json`, merge it over the defaults, and configure Loguru from the merged result.
- Keep the effective logging configuration externalizable rather than hard-coding handler counts, targets, levels, formats, colorization, rotation, or retention.
- Default logging should provide:
  - a plain-text datestamped application log under `logs/`
  - a colorized stdout handler
  - a colorized stderr handler
- Default routing should send:
  - `info`, `warning`, and `error` to the application log
  - `info` and `warning` to stdout
  - only `error` to stderr
- Log entrypoint parameters at `info` level.
- Include thread ID, source file, and source line in application log entries.
- Compress log files older than 7 days into `logs/archive/`.
- Delete archived logs older than 30 days.
- `src/app_logging.py` should contain only project-specific logging glue such as interception, path normalization, and archive housekeeping.

## 14. Spell Checking
- Run `npm run spellcheck` after every project change.
- If `cspell` reports a possible spelling error, first check whether the existing spelling is valid in context by querying Google.
- If the spelling is valid in context, add it to `cspell-words.txt`.
- Keep `cspell-words.txt` alphabetically ordered.
- If the spelling is not valid in context, fix the source instead of adding it to the dictionary.

## 15. Static Analysis
- Use `pyright` as the main static-analysis guardrail and fix what it reports before finishing unless explicitly approved otherwise.
- After source files are added, changed, or removed, run `ruff check .` and fix the issues it reports.
- After source files are added, changed, or removed, run `pyupgrade` across the Python source files and keep the resulting modernizations unless there is a clear project-specific reason not to.
- Do not leave unresolved type, import, symbol, or unused-import warnings.
- Keep null guards and type signatures aligned.
- After introducing new symbols or moving imports or constants, do a quick import and symbol sanity pass in addition to tests and static analysis.
- Treat static analysis as part of the required final quality bar.
