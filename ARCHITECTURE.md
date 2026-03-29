# Architecture Contract

Apply this contract to new Python code and refactors in this repository unless explicitly instructed otherwise.

## 1. Design
- Prefer small, focused classes when behavior has dependencies.
- Use inversion of control (IoC) by default.
- Inject collaborators through constructors; do not construct them inside business classes.
- Prefer composition over inheritance.

## 2. Dependencies
- Define injectable collaborator protocols in `src/protocols.py`, including `ILogger` for business-class logging.
- Depend on protocols rather than concrete implementations.
- `main.py` owns application wiring and top-level configuration.
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
- Every user-facing or externally triggered entry point must have its own sequence diagram source rather than relying only on a shared summary diagram. Identify entry points by analyzing the current code rather than maintaining a hard-coded list in this contract.
- Shared overview diagrams may exist in addition to per-entrypoint diagrams, but they do not replace entrypoint-specific sequence diagrams.
- Distinct entry-point variations and code paths should be diagramed in their own sequence diagrams whenever the behavior, collaborators, or observable outcomes differ in a meaningful way.
- When class structure changes, update the PlantUML class diagram.
- After diagram updates, generate fresh PNG outputs from the updated PlantUML sources using the official PlantUML render server.
- Keep `README.md` generated and up to date with a concise description of the current implementation.
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
- Keep implementations simple and readable.
- Prefer explicit names over terse ones.
- Use ASCII unless the file already requires Unicode.
- Add concise code comments when they clarify what the code is doing and why, especially around non-obvious logic or integration boundaries.

## 12. Formatting
- Run `black .` from the repository root whenever project contents are updated.
- Treat formatter output as part of the required final state.

## 13. Logging
- Include `trace`, `info`, `warn`, and `error` logging where appropriate.
- Use `@traced` from `autologging` on concrete methods in application source so method entry and exit tracing is applied consistently.
- Business classes should depend on `ILogger` via constructor injection.
- Instantiate one shared logging singleton in `main.py` and pass that same object into business objects across the project.
- Integrate standard logging with Loguru through an `InterceptHandler`.
- Store the default Loguru configuration object in `src/defaults.py`.
- Read `config/loguru.json` from the filesystem as an override layer, merge it over the default configuration from `src/defaults.py`, and use the merged result to configure Loguru through `loguru-config`.
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

## 14. Static Analysis
- Use `pyright` as the project-level static analysis guardrail and fix the issues it reports before finishing a task unless explicitly approved otherwise.
- Do not leave unresolved type, import, symbol, or unused-import warnings.
- Keep null guards and type signatures aligned so impossible-condition warnings are avoided.
- After introducing new symbols or moving imports or constants, run a quick import and symbol sanity pass in addition to tests, `pyright`, and mypy.
- Add an explicit lint step for unused imports and address any findings before finishing a task.
- Treat static analysis as part of the quality bar alongside formatting, `pyright`, tests, and mypy.