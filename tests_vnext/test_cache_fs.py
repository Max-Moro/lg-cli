from pathlib import Path
from lg_vnext.cache.fs_cache import Cache

def test_cache_processed_and_tokens(tmp_path: Path):
    cache = Cache(tmp_path, enabled=True, tool_version="T")
    absf = tmp_path / "f.txt"; absf.write_text("hello", encoding="utf-8")
    k_proc, p_proc = cache.build_processed_key(abs_path=absf, adapter_name="markdown", adapter_cfg={"lvl":2}, group_size=1, mixed=False)
    cache.put_processed(p_proc, processed_text="HELLO", meta={"removed_h1":0})
    assert cache.get_processed(p_proc)
    cache.update_tokens(p_proc, model="o3", mode="processed", value=123)
    assert cache.get_tokens(p_proc, model="o3", mode="processed") == 123

def test_cache_raw_tokens(tmp_path: Path):
    cache = Cache(tmp_path, enabled=True, tool_version="T")
    absf = tmp_path / "f.txt"; absf.write_text("hello", encoding="utf-8")
    k_raw, p_raw = cache.build_raw_tokens_key(abs_path=absf)
    assert cache.get_tokens(p_raw, model="o3", mode="raw") is None
    cache.update_tokens(p_raw, model="o3", mode="raw", value=7)
    assert cache.get_tokens(p_raw, model="o3", mode="raw") == 7

def test_cache_rendered_tokens(tmp_path: Path):
    cache = Cache(tmp_path, enabled=True, tool_version="T")
    k_r, p_r = cache.build_rendered_key(
        context_name="ctx:a",
        sections_used={"docs":1},
        options_fp={"mode":"all","code_fence":True,"model":"o3","markdown":{"max_heading_level":2}},
        processed_keys={"README.md":"abc123"}
    )
    assert cache.get_rendered_tokens(p_r, model="o3") is None
    cache.update_rendered_tokens(p_r, model="o3", value=999)
    assert cache.get_rendered_tokens(p_r, model="o3") == 999
