from pathlib import Path

from lg.engine import run_report
from lg.types import RunOptions


def test_processed_cache_skips_adapter_on_second_run(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)

    # исходники
    (tmpproj / "m.py").write_text("print('ok')\n", encoding="utf-8")

    # счётчик вызовов process у PythonAdapter
    calls = {"process": 0}

    import lg.adapters.python as py_ad
    orig_process = py_ad.PythonAdapter.process

    def wrapped_process(self, text, cfg, group_size, mixed):
        calls["process"] += 1
        return orig_process(self, text, cfg, group_size, mixed)

    monkeypatch.setattr(py_ad.PythonAdapter, "process", wrapped_process, raising=True)

    # первый прогон — адаптер обязан сработать
    r1 = run_report("sec:all", RunOptions())
    assert r1.total.tokensProcessed > 0
    assert calls["process"] >= 1

    # второй прогон — ничего не меняем → берём processed из кэша
    r2 = run_report("sec:all", RunOptions())
    assert r2.total.tokensProcessed == r1.total.tokensProcessed
    # процессингов быть не должно
    assert calls["process"] == 1

def test_token_counts_cached_between_runs(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)
    (tmpproj / "x.md").write_text("# T\nbody\n", encoding="utf-8")

    # подменяем _enc_for_model, чтобы считать вызовы encode()
    import lg.stats.tokenizer as tok

    class FakeEnc:
        def __init__(self, counter):
            self.counter = counter
        def encode(self, s: str):
            self.counter["encode"] += 1
            # простая «токенизация»: длина в символах
            return list(s)

    counter = {"encode": 0}
    def fake_enc_for_model(model: str):
        info = tok._EncInfo(model=model, ctx_limit=32000, enc_name="fake", enc=FakeEnc(counter))
        return info

    monkeypatch.setattr(tok, "_enc_for_model", fake_enc_for_model, raising=True)

    # первый запуск — посчитает raw/processed + rendered (итоговый и sections-only)
    r1 = run_report("sec:docs", RunOptions(model="o3"))
    enc_calls_first = counter["encode"]
    assert enc_calls_first > 0

    # второй запуск — должен брать ВСЕ токены из кэша → encode не зовётся
    r2 = run_report("sec:docs", RunOptions(model="o3"))
    assert counter["encode"] == enc_calls_first

def test_rendered_tokens_cached(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)
    # контекст a: "Intro\n\n${docs}\n"
    (tmpproj / "README.md").write_text("# A\nZ\n", encoding="utf-8")

    import lg.stats.tokenizer as tok

    class FakeEnc:
        def __init__(self, counter):
            self.counter = counter
        def encode(self, s: str):
            self.counter["encode"] += 1
            return list(s)

    counter = {"encode": 0}
    def fake_enc_for_model(model: str):
        return tok._EncInfo(model=model, ctx_limit=32000, enc_name="fake", enc=FakeEnc(counter))

    monkeypatch.setattr(tok, "_enc_for_model", fake_enc_for_model, raising=True)

    # первый запуск (посчитает rendered для final и sections-only)
    r1 = run_report("ctx:a", RunOptions())
    calls1 = counter["encode"]
    assert calls1 >= 2  # final + sections-only

    # второй запуск (ничего не меняем) — оба rendered должны прийти из кэша
    r2 = run_report("ctx:a", RunOptions())
    assert counter["encode"] == calls1