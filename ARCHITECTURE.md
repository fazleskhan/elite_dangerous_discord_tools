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
- Return sentinel values only when explicitly required by the feature contract.

## 7. Testing
- Add or update tests for every behavior change.
- Use stubs or fakes for unit tests.
- Use real collaborators together in integration tests.
- Cover constructor null guards, argument validation, happy paths, and failure paths.
- Type pytest fixtures explicitly where useful, for example `pytest.MonkeyPatch` and `pytest.CaptureFixture[str]`.

## 8. Diagrams
- When command-line behavior changes, update the related PlantUML sequence diagram or create one if it does not exist.
- When class structure changes, update the PlantUML class diagram.
- After diagram updates, generate fresh PNG outputs from the updated PlantUML sources using the official PlantUML render server.
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
- Add comments only when they explain non-obvious intent.

## 12. Formatting
- Run `black .` from the repository root whenever project contents are updated.
- Treat formatter output as part of the required final state.

## 14. Static Analysis
- Address Pylance-reported problems before finishing a task unless explicitly approved otherwise.
- Do not leave unresolved type, import, symbol, or unused-import warnings.
- Keep null guards and type signatures aligned so impossible-condition warnings are avoided.
- After introducing new symbols or moving imports or constants, run a quick import and symbol sanity pass in addition to tests and mypy.
- Add an explicit lint step for unused imports and address any findings before finishing a task.
- Treat static analysis as part of the quality bar alongside formatting, tests, and mypy.

