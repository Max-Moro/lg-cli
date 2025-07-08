from lg.filters.model import FilterNode
from lg.filters.engine import FilterEngine


def _engine():
    # корень default-allow, но блочим *.log
    root = FilterNode(
        mode="block",
        block=["**/*.log"],
        children={
            "secure": FilterNode(
                mode="allow",
                allow=["*.py"],
                block=["*_secret.py"],
            )
        },
    )
    return FilterEngine(root)


def test_block_global_log():
    eng = _engine()
    assert eng.includes("src/app.py")
    assert not eng.includes("src/debug.log")


def test_secure_allow_only_py():
    eng = _engine()
    assert eng.includes("secure/auth.py")
    assert not eng.includes("secure/readme.md")
    assert not eng.includes("secure/data_secret.py")
