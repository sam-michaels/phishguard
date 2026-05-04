"""URL heuristics tests."""
from app.services.url_analysis.heuristics import check_heuristics


def _names(results) -> set[str]:
    return {r.name for r in results if r.triggered}


def test_clean_url_triggers_nothing():
    assert _names(check_heuristics("https://www.google.com/")) == set()


def test_ip_host_detected():
    assert "ip_host" in _names(check_heuristics("http://192.168.1.1/login"))


def test_at_symbol_detected():
    assert "at_symbol" in _names(check_heuristics("https://attacker.com@evil.com/"))


def test_suspicious_tld_detected():
    assert "suspicious_tld" in _names(check_heuristics("https://my-bank.tk/"))


def test_punycode_detected():
    assert "punycode" in _names(check_heuristics("https://xn--pple-43d.com/"))


def test_excessive_subdomains_detected():
    assert "excessive_subdomains" in _names(
        check_heuristics("https://a.b.c.d.e.example.com/")
    )
