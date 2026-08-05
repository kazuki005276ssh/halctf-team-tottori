from halctf.tools.flag_submit import extract_flag

PATTERN = r"flag\{[^}]+\}"


def test_extract_basic():
    assert extract_flag("本文: flag{abc_123} 以上", PATTERN) == "flag{abc_123}"


def test_extract_none():
    assert extract_flag("フラグは見つからなかった", PATTERN) is None


def test_extract_first_match():
    text = "flag{first} と flag{second}"
    assert extract_flag(text, PATTERN) == "flag{first}"


def test_extract_custom_pattern():
    assert extract_flag("HALCTF{xyz}", r"HALCTF\{[^}]+\}") == "HALCTF{xyz}"
