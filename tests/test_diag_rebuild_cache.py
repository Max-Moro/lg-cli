from pathlib import Path

from lg.cache.fs_cache import Cache
from lg.engine import run_report
from lg.types import RunOptions
from .infrastructure import run_cli, jload


def test_diag_rebuild_cache_clears_and_repairs(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)

    # 1) прогоняем пайплайн, чтобы нагенерить кэш (processed/raw/rendered)
    (tmpproj / "README.md").write_text("# Title\nbody\n", encoding="utf-8")
    run_report("sec:all", RunOptions())

    cache = Cache(tmpproj, enabled=True, tool_version="T")
    snap1 = cache.snapshot()
    assert snap1.exists and snap1.entries > 0, "ожидали непустой кэш после пайплайна"

    # 2) добавим заведомо битую запись в кэш (эмулируем «сломанный» кэш)
    bad = cache.dir / "processed" / "zz" / "yy" / "broken.json"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("{not-a-valid-json", encoding="utf-8")

    # убедимся, что snapshot «пережёвывает» даже битые файлы и считает их как entries
    snap_with_broken = cache.snapshot()
    assert snap_with_broken.entries >= snap1.entries

    # 3) запускаем CLI-диагностику БЕЗ флага --rebuild-cache: кэш остаётся как есть
    cp_no = run_cli(tmpproj, "diag")
    assert cp_no.returncode == 0, cp_no.stderr
    d_no = jload(cp_no.stdout)
    assert d_no["cache"]["exists"] is True
    assert d_no["cache"]["entries"] >= snap_with_broken.entries

    # 4) теперь запускаем CLI-диагностику С флагом --rebuild-cache: кэш должен быть очищен
    cp_re = run_cli(tmpproj, "diag", "--rebuild-cache")
    assert cp_re.returncode == 0, cp_re.stderr
    d_re = jload(cp_re.stdout)
    assert d_re["cache"]["rebuilt"] is True
    # после rebuild каталог существует, но пуст
    assert d_re["cache"]["exists"] is True
    assert d_re["cache"]["entries"] == 0
    assert d_re["cache"]["sizeBytes"] == 0
