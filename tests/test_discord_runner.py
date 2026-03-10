import pytest

import discord_runner


def test_discord_runner_main_runs_bot(monkeypatch: pytest.MonkeyPatch) -> None:
    run_calls: list[str] = []

    class FakeBot:
        def run(self) -> None:
            run_calls.append("run")

    monkeypatch.setattr(discord_runner.EDDiscordBot, "create", staticmethod(lambda: FakeBot()))
    monkeypatch.setattr(discord_runner.logger, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(discord_runner.logger, "debug", lambda *args, **kwargs: None)
    monkeypatch.setattr(discord_runner.logger, "exception", lambda *args, **kwargs: None)

    discord_runner.main()
    assert run_calls == ["run"]


def test_discord_runner_main_logs_and_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    errors: list[str] = []

    class FakeBot:
        def run(self) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(discord_runner.EDDiscordBot, "create", staticmethod(lambda: FakeBot()))
    monkeypatch.setattr(discord_runner.logger, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(discord_runner.logger, "debug", lambda *args, **kwargs: None)
    monkeypatch.setattr(discord_runner.logger, "exception", lambda *args, **kwargs: errors.append("logged"))

    with pytest.raises(RuntimeError, match="boom"):
        discord_runner.main()

    assert errors == ["logged"]
