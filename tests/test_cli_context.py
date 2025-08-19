from .conftest import run_cli

def test_cli_report_missing_context_exits_nonzero(tmpproj):
    # контекста ctx:missing нет → код возврата ненулевой, stderr содержит ошибку
    cp = run_cli(tmpproj, "report", "ctx:missing")
    assert cp.returncode != 0
    assert "Context template not found" in (cp.stderr or "")

def test_cli_render_section_smoke(tmpproj):
    # секция docs существует (см. фикстуру tmpproj), команда завершается успешно
    cp = run_cli(tmpproj, "render", "sec:docs")
    assert cp.returncode == 0, cp.stderr
    # Ничего конкретного про содержимое не утверждаем: текст зависит от файлов проекта
    assert isinstance(cp.stdout, str)
    # гарантируем, что хоть как-то отрендерилось (в т.ч. пустая строка допустима)
    assert cp.stdout is not None
