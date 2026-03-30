# Architecture Contract

Apply this contract to new Python code and refactors in this repository unless explicitly instructed otherwise.

## Project-Specific Companion
- This file defines the shared base architecture contract for the repository.
- A repository may include a project-specific companion file at `ARCHITECTURE.project.md`.
- When present, `ARCHITECTURE.project.md` must be read together with this file and may add repository-specific requirements, constraints, diagrams, workflow rules, and implementation variations.
- Repository-specific overrides must be explicit. If a rule in `ARCHITECTURE.project.md` conflicts with this file, the project-specific rule takes precedence for this repository.
- Prefer keeping reusable rules in `ARCHITECTURE.md` and moving only repository-specific variations into `ARCHITECTURE.project.md`.

## 1. Design
- Prefer small, focused classes when behavior has dependencies.
- Use inversion of control (IoC) by default.
- Inject collaborators through constructors; do not construct them inside business classes.
- Prefer composition over inheritance.

## 2. Dependencies
- Define injectable collaborator protocols in `src/protocols.py`, including `ILogger` for business-class logging.
- Depend on protocols rather than concrete implementations.
- `main.py` owns application wiring and top-level configuration.
- Maintain `requirements.txt` for Python dependencies needed in deployed production environments.
- Maintain `dev-requirements.txt` for Python dependencies needed only for local development, testing, linting, typing, profiling, or other non-production workflows.
- When reloading Python dependencies in a development environment, install both `requirements.txt` and `dev-requirements.txt`.
- Add new Python dependencies to `dev-requirements.txt` by default unless they are required while the application is deployed in production, in which case add them to `requirements.txt`.
- Always make changes on the branch currently active in the user's workspace unless the user explicitly asks to switch branches.

## 3. Null Safety
- Add runtime null guards for constructor arguments and public method arguments that come from outside the class.
- If a value is null-guarded, annotate it with `| None`.
- Null guard failures should raise `ValueError` with clear messages like `"<arg_name> must not be null"`.

## 4. Typing
- Fully type constructor arguments, method arguments, return values, instance fields, constants, and important locals.
- Prefer precise types over `Any`.
- Use `Path` for filesystem paths.
- Keep the code free of type-checker warnings.

## 5. Module Responsibilities
- `main.py` owns CLI parsing, default paths, wiring, and configuration bootstrap.
- Business classes should not own CLI concerns.
- Keep environment-specific defaults near the entry point unless there is a strong reason not to.
- Avoid hidden global state.
- Do not create module names that conflict with Python standard library modules.
- Do not introduce shim or compatibility-layer modules; integrate dependencies directly and use type stubs or normal refactoring instead of project-owned wrapper layers.

## 6. Error Handling
- Prefer defensive programming: validate inputs early, guard assumptions, and fail clearly when invariants are violated.
- Fail fast on invalid inputs.
- Use clear, deterministic errors for invalid arguments and invalid file or content formats.
- Handled errors should not generate a traceback; show only a clear, concise message explaining the issue.
- Log handled errors only once at the CLI boundary. Business logic should raise clear handled exceptions without separately logging them as errors.
- Unhandled errors should preserve the traceback for debugging.
- Return sentinel values only when explicitly required by the feature contract.

## 7. Testing
- Add or update tests for every behavior change.
- Use stubs or fakes for unit tests.
- Use real collaborators together in integration tests.
- Cover constructor null guards, argument validation, happy paths, and failure paths.
- Type pytest fixtures explicitly where useful, for example `pytest.MonkeyPatch` and `pytest.CaptureFixture[str]`.

## 8. Diagrams
- When application behavior changes, update the related PlantUML sequence diagrams or create them if they do not exist.
- Treat diagram maintenance as mandatory for source additions, deletions, renames, wiring changes, collaborator changes, control-flow changes, entrypoint changes, logging/configuration flow changes, and structural refactors, even when the user-facing behavior is intended to stay the same.
- Every user-facing or externally triggered entry point must have its own sequence diagram source rather than relying only on a shared summary diagram. Identify entry points by analyzing the current code rather than maintaining a hard-coded list in this contract.
- Shared overview diagrams may exist in addition to per-entrypoint diagrams, but they do not replace entrypoint-specific sequence diagrams.
- Distinct entry-point variations and code paths should be diagrammed in their own sequence diagrams whenever the behavior, collaborators, or observable outcomes differ in a meaningful way.
- When class structure changes, update the PlantUML class diagram.
- A task that changes relevant code is incomplete until the affected `.puml` sources have been reviewed and updated to match the current code, and any stale diagrams have been removed or replaced.
- After diagram updates, generate fresh PNG outputs for every updated PlantUML source (`.puml`) before finishing the task.
- Do not defer diagram rendering; generate the PNGs in the same task immediately after updating the `.puml` files.
- Write each PNG next to its source file with the same basename (for example `foo.puml` -> `foo.png`).
- Use a local PlantUML renderer when available; otherwise render through the official PlantUML server.
- Treat missing or stale diagram PNG generation as an incomplete task state.
- Keep `README.md` generated and up to date with a concise description of the current implementation.
- When regenerating `README.md`, use `docs/README_TEMPLATE.md` as the required structural template and model.
- Keep mutable README narrative content in Python module docstrings and script comment blocks, including `scripts/postCreateCommand.sh`, using tagged sections in the form `[README:<KEY>] ... [/README]`.
- Use class and method docstrings as source material when generating implementation-oriented README content such as code-overview or component-summary sections.
- In `docs/README_TEMPLATE.md`, reference docstring-backed content through placeholders in the form `{{README:<KEY>}}`.
- Assemble the final `README.md` by applying the collected tagged sections and generated docstring-derived sections from Python modules and script sources to `docs/README_TEMPLATE.md` via `python scripts/generate_readme.py`.
- `README.md` must include an `Entrypoints` section that documents every current user-facing or externally triggered entrypoint (for example CLI commands, bot commands, and utility scripts).
- For each documented entrypoint, include a short behavioral overview plus the available arguments/options, and clearly identify required versus optional arguments and defaults when present.
- Include a link to `BUSINESS.md` in `README.md` so the business rules are discoverable alongside the implementation summary.
- Keep `BUSINESS.md` focused on detailed business logic and user-visible behavior that is not already fully specified in `ARCHITECTURE.md`.
- When behavior changes, analyze the current code and update `BUSINESS.md` with any business-rule changes that are found.
- `BUSINESS.md` should capture concrete command behavior, workflow rules, data-handling rules, cache behavior, integration-facing behavior, and user-visible constraints when those details are more specific than the architectural contract.
- Avoid duplicating architecture-only concerns in `BUSINESS.md`; prefer `ARCHITECTURE.md` for implementation rules and `BUSINESS.md` for feature and behavior rules.
- Include the current diagram PNGs inline in `README.md` so they render in the README, and include source links alongside them.

## 9. CLI
- Use `argparse` for command-line interfaces.
- Do not use `print()` for application output; route user-facing messages through logging.
- Keep CLI parsing separate from domain logic.

## 10. Refactoring
- Preserve behavior unless the requested change explicitly changes behavior.
- When introducing IoC, update tests to reflect the new wiring.
- When adding null guards, update type signatures to match.

## 11. Style
- Store shared magic string constants in `src/constants.py`.
- Store default arguments and default values in `src/defaults.py`.
- Prefer named constants over repeated inline string literals in source files.
- Use Pythonic code style throughout the project rather than Java-style ceremony or patterns.
- Prefer guard clauses and direct assignment over `if ... else` assignment blocks.
- Prefer direct construction over trivial constructor-only factory wrappers unless the wrapper adds real wiring or behavior.
- Do not add placeholder no-op `main()` functions to non-entrypoint modules.
- Keep implementations simple and readable.
- Prefer explicit names over terse ones.
- Use ASCII unless the file already requires Unicode.
- Add concise code comments when they clarify what the code is doing and why, especially around non-obvious logic or integration boundaries.
- Add a docstring to every class and every method.
- Each class docstring must describe the class's overall purpose and give a short overview of how it achieves that purpose.
- Each method docstring must describe the method's purpose and give a short overview of how it achieves its result, especially when it coordinates collaborators, performs validation, bridges sync/async work, or maintains caches or locks.
- After source files are added, changed, renamed, or removed from the project, review the affected class and method docstrings and update, add, move, or delete them so they continue to match the current logic, collaborators, and structure.
- Treat stale or missing class and method docstrings as defects.
- After source files are added, changed, renamed, or removed from the project, review the surrounding clarifying code comments and update, add, move, or delete them so they continue to match the current logic and its purpose.
- Treat stale explanatory comments as defects: comments must not describe removed behavior, old control flow, old collaborators, or pre-refactor structure.

## 12. Formatting
- After source files are added, changed, or removed from the project, run `black .` from the repository root before finishing the task.
- Treat formatter output as part of the required final state.
- When adding a VS Code extension for the workspace, add it to the `.devcontainer/devcontainer.json` `customizations.vscode.extensions` array.

## 13. Logging
- Include `trace`, `info`, `warn`, and `error` logging where appropriate.
- Use `@traced` from `autologging` on concrete methods in application source so method entry and exit tracing is applied consistently.
- Business classes should depend on `ILogger` via constructor injection.
- Instantiate one shared logging singleton in `main.py` and pass that same object into business objects across the project.
- Integrate standard logging with Loguru through an `InterceptHandler`.
- Keep project-specific logging glue in a dedicated application logging module, for example `src/app_logging.py`.
- Store the default Loguru configuration object in a shared defaults module, for example `src/defaults.py`.
- Read a filesystem configuration file, for example `config/loguru.json`, as an override layer, merge it over the default configuration, and use the merged result to configure Loguru through `loguru-config`.
- Keep the effective Loguru configuration shape externalizable through `config/loguru.json`; handler count, targets, levels, formats, colorization, rotation, and retention settings should be overridable there rather than hard-coded in code.
- The default configuration should provide:
  - a plain-text datestamped application log under `logs/`
  - a colorized stdout handler
  - a colorized stderr handler
- Default behavior should send `info`, `warn`, and `error` to the application log, `info` and `warn` to stdout, and only `error` to stderr.
- Log parameters received by application entry points at `info` level.
- Application log entries should include thread ID, source file, and source line.
- Log files older than 7 days should be compressed into `logs/archive/`.
- Archived logs older than 30 days should be deleted.
- Handled CLI errors should be logged once at the CLI boundary and should not emit a traceback.
- Unhandled exceptions should preserve their traceback for debugging.
- `src/app_logging.py` should contain only project-specific logging glue such as interception, path normalization, and archive housekeeping.

## 14. Spell Checking
- Run `npm run spellcheck` from the repository root after making any project change and treat the result as part of the required final state.
- If `cspell` reports a possible spelling error, first determine whether the existing spelling is commonly correct for this project's context by querying Google.
- If the existing spelling is valid in context, add that word to `cspell-words.txt`.
- Keep the words in `cspell-words.txt` in alphabetical order.
- If the existing spelling is not valid in context, fix the spelling in the source instead of adding it to the dictionary.

## 15. Static Analysis
- Use `pyright` as the project-level static analysis guardrail and fix the issues it reports before finishing a task unless explicitly approved otherwise.
- After source files are added, changed, or removed from the project, run `ruff check .` from the repository root and fix the issues it identifies before finishing the task.
- After source files are added, changed, or removed from the project, run `pyupgrade` across the Python source files and keep the resulting modernizations unless there is a clear project-specific reason not to.
- Do not leave unresolved type, import, symbol, or unused-import warnings.
- Keep null guards and type signatures aligned so impossible-condition warnings are avoided.
- After introducing new symbols or moving imports or constants, run a quick import and symbol sanity pass in addition to tests, `pyright`, and mypy.
- Add an explicit lint step for unused imports and address any findings before finishing a task.
- Treat static analysis as part of the quality bar alongside formatting, `pyright`, tests, and mypy.
