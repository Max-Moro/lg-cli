from pathlib import Path

from lg.engine import run_report
from lg.types import RunOptions


def test_processed_cache_skips_adapter_on_second_run(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)

    # source files
    (tmpproj / "m.py").write_text("print('ok')\n", encoding="utf-8")

    # call counter for PythonAdapter.process
    calls = {"process": 0}

    import lg.adapters.python.adapter as py_ad
    orig_process = py_ad.PythonAdapter.process

    def wrapped_process(self, lightweight_ctx):
        calls["process"] += 1
        return orig_process(self, lightweight_ctx)

    monkeypatch.setattr(py_ad.PythonAdapter, "process", wrapped_process, raising=True)

    # first run - adapter must execute
    r1 = run_report("sec:all", RunOptions())
    assert r1.total.tokensProcessed > 0
    assert calls["process"] >= 1

    # second run - nothing changes -> use processed from cache
    r2 = run_report("sec:all", RunOptions())
    assert r2.total.tokensProcessed == r1.total.tokensProcessed
    # processing should not happen again
    assert calls["process"] == 1


def test_token_counts_cached_between_runs(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)
    (tmpproj / "x.md").write_text("# T\nbody\n", encoding="utf-8")

    # Encode call counter
    counter = {"encode": 0}

    # Mock count_tokens in TokenService to track calls
    from lg.stats.tokenizer import TokenService
    orig_count = TokenService.count_text

    def wrapped_count(self, text: str) -> int:
        counter["encode"] += 1
        return orig_count(self, text)

    monkeypatch.setattr(TokenService, "count_text", wrapped_count, raising=True)

    # first run - count raw/processed + rendered (final and sections-only)
    r1 = run_report("sec:docs", RunOptions())
    enc_calls_first = counter["encode"]
    assert enc_calls_first > 0

    # second run - should get ALL tokens from cache -> encode not called
    r2 = run_report("sec:docs", RunOptions())
    # Cache works through count_text_cached, but basic count_text should not be called more
    assert counter["encode"] == enc_calls_first


def test_rendered_tokens_cached(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)
    # context a: "Intro\n\n${docs}\n"
    (tmpproj / "README.md").write_text("# A\nZ\n", encoding="utf-8")

    # Call counter
    counter = {"encode": 0}

    # Mock count_tokens in TokenService to track calls
    from lg.stats.tokenizer import TokenService
    orig_count = TokenService.count_text

    def wrapped_count(self, text: str) -> int:
        counter["encode"] += 1
        return orig_count(self, text)

    monkeypatch.setattr(TokenService, "count_text", wrapped_count, raising=True)

    # first run (count rendered for final and sections-only)
    r1 = run_report("ctx:a", RunOptions())
    calls1 = counter["encode"]
    assert calls1 >= 2  # final + sections-only

    # second run (nothing changes) - both rendered should come from cache
    r2 = run_report("ctx:a", RunOptions())
    # Everything should come from cache
    assert counter["encode"] == calls1
