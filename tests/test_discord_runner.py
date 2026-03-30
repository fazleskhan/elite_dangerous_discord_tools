import pytest

import discord_runner


def test_discord_runner_main_runs_bot(monkeypatch: pytest.MonkeyPatch) -> None:
    run_calls: list[str] = []
    received_loggers: list[object] = []

    class FakeBot:
        def run(self) -> None:
            run_calls.append("run")

    monkeypatch.setattr(
        discord_runner.EDDiscordBot,
        "create",
        staticmethod(
            lambda logger=None: (
                received_loggers.append(logger),
                FakeBot(),
            )[1]
        ),
    )
    monkeypatch.setattr(discord_runner.logger, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(discord_runner.logger, "debug", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        discord_runner.logger, "exception", lambda *args, **kwargs: None
    )

    discord_runner.main()
    assert run_calls == ["run"]
    assert received_loggers == [discord_runner.logger]


def test_discord_runner_main_logs_and_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    errors: list[str] = []
    received_loggers: list[object] = []

    class FakeBot:
        def run(self) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(
        discord_runner.EDDiscordBot,
        "create",
        staticmethod(
            lambda logger=None: (
                received_loggers.append(logger),
                FakeBot(),
            )[1]
        ),
    )
    monkeypatch.setattr(discord_runner.logger, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(discord_runner.logger, "debug", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        discord_runner.logger,
        "exception",
        lambda *args, **kwargs: errors.append("logged"),
    )

    with pytest.raises(RuntimeError, match="boom"):
        discord_runner.main()

    assert errors == ["logged"]
    assert received_loggers == [discord_runner.logger]
