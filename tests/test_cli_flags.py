from lg.cli import _build_parser

def test_parser_code_fence_and_max_heading_level():
    parser = _build_parser()
    args = parser.parse_args(["--code-fence", "--max-heading-level", "4"])
    assert args.code_fence is True
    assert args.max_heading_level == 4

def test_parser_defaults():
    parser = _build_parser()
    args = parser.parse_args([])
    assert args.code_fence is False
    assert args.max_heading_level is None
