# Elite Dangerous Discord Tools

Elite Dangerous Discord Tools is a Python application for route lookup, system inspection, datasource import/export, and Discord bot access over the same route and cache services. The project uses constructor injection, protocol-based composition, and a shared Loguru-backed logging singleton wired from the application entry points.

## Implementation Summary
- `src/main.py` provides the CLI for `ping`, `path`, `system_info`, `all_loaded_systems`, `calc_systems_distance`, `init_datasource`, and `bulk_load_cache`.
- `src/ed_route.py` is the thin route-service facade over focused delegate services.
- `src/ed_route_service_factory.py` composes datasource, cache, BFS, and service collaborators.
- `src/app_logging.py` owns project-specific logging glue such as standard-logging interception, config watching, path normalization, and archive housekeeping.
- TinyDB and Redis import/export entry points reuse the same logging singleton and backend factories.
- `src/ed_discord_bot.py` exposes the same route and cache operations through Discord commands.

## Business Rules
- Business rules are documented in [BUSINESS.md](BUSINESS.md).

## Diagrams
- CLI entrypoint sequence sources: [docs/diagrams/cli](docs/diagrams/cli)
- Discord entrypoint sequence sources: [docs/diagrams/discord](docs/diagrams/discord)
- Current class structure source: [docs/diagrams/class_structure.puml](docs/diagrams/class_structure.puml)

## Notes
- Diagram PNGs are not checked in yet in this workspace because local PlantUML rendering is unavailable here and the official PlantUML render server cannot be reached from the restricted environment.
