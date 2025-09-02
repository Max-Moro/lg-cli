from pathlib import Path

from lg.engine import run_report
from lg.types import RunOptions


def test_processed_cache_skips_adapter_on_second_run(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)

    # исходники
    (tmpproj / "m.py").write_text("print('ok')\n", encoding="utf-8")

    # счётчик вызовов process у PythonAdapter
    calls = {"process": 0}

    import lg.adapters.python_tree_sitter as py_ad
    orig_process = py_ad.PythonTreeSitterAdapter.process

    def wrapped_process(self, text, group_size, mixed):
        calls["process"] += 1
        return orig_process(self, text, group_size, mixed)

    monkeypatch.setattr(py_ad.PythonTreeSitterAdapter, "process", wrapped_process, raising=True)

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

    # Мокаем get_model_info и tiktoken.get_encoding
    from lg.stats import ResolvedModel
    import lg.stats as lg_models
    import tiktoken

    class FakeEnc:
        def __init__(self, counter):
            self.counter = counter
        def encode(self, s: str):
            self.counter["encode"] += 1
            # простая «токенизация»: длина в символах
            return list(s)

    counter = {"encode": 0}

    def fake_get_model_info(_root, selector: str):
        # эффективный лимит 32K, энкодер "fake"
        return ResolvedModel(
            name=selector, base="o3", provider="openai",
            encoder="fake", ctx_limit=32_000, plan=None
        )

    monkeypatch.setattr(lg_models, "get_model_info", fake_get_model_info, raising=True)
    monkeypatch.setattr(tiktoken, "get_encoding", lambda *_args, **_kw: FakeEnc(counter), raising=True)

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

    # Мокаем get_model_info и tiktoken.get_encoding
    from lg.stats import ResolvedModel
    import lg.stats as lg_models
    import tiktoken

    class FakeEnc:
        def __init__(self, counter):
            self.counter = counter
        def encode(self, s: str):
            self.counter["encode"] += 1
            return list(s)

    counter = {"encode": 0}

    def fake_get_model_info(_root, selector: str):
        return ResolvedModel(
            name=selector, base="o3", provider="openai",
            encoder="fake", ctx_limit=32_000, plan=None
        )

    monkeypatch.setattr(lg_models, "get_model_info", fake_get_model_info, raising=True)
    monkeypatch.setattr(tiktoken, "get_encoding", lambda *_args, **_kw: FakeEnc(counter), raising=True)

    # первый запуск (посчитает rendered для final и sections-only)
    r1 = run_report("ctx:a", RunOptions())
    calls1 = counter["encode"]
    assert calls1 >= 2  # final + sections-only

    # второй запуск (ничего не меняем) — оба rendered должны прийти из кэша
    r2 = run_report("ctx:a", RunOptions())
    assert counter["encode"] == calls1