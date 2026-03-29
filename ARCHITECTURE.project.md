# Project-Specific Architecture Companion

Read this file together with [ARCHITECTURE.md](ARCHITECTURE.md).

## Purpose
- This file captures repository-specific architectural requirements, implementation variations, and explicit overrides for Elite Dangerous Discord Tools.
- Unless this file explicitly overrides a rule, the base contract in `ARCHITECTURE.md` still applies.

## Repository-Specific Entry Points
- The primary application entry points are [src/main.py](src/main.py) for the CLI and [src/ed_discord_bot.py](src/ed_discord_bot.py) for Discord-triggered behavior.
- When code changes add, remove, or materially alter externally reachable entry points in these modules or in future entrypoint modules, update the related sequence diagrams.

## Repository-Specific Diagram Layout
- Store CLI entrypoint sequence sources under `docs/diagrams/cli/`.
- Store Discord entrypoint sequence sources under `docs/diagrams/discord/`.
- Store shared structure diagrams, such as class diagrams, directly under `docs/diagrams/` unless a more specific folder becomes necessary.
- Remove stale or superseded diagram sources when a clearer authoritative location replaces them.

## Repository-Specific Documentation Split
- Keep cross-project rules in [ARCHITECTURE.md](ARCHITECTURE.md).
- Keep repository-specific architectural variations in [ARCHITECTURE.project.md](ARCHITECTURE.project.md).
- Keep feature and business behavior in [BUSINESS.md](BUSINESS.md).
