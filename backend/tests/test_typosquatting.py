"""Typosquatting detection tests."""
from app.services.url_analysis.typosquatting import check_typosquatting


def test_legitimate_domain_not_flagged():
    result = check_typosquatting("https://www.paypal.com/login")
    assert result.triggered is False


def test_one_edit_typo_flagged_high():
    # 'paypa1' = 1 substitution from 'paypal'
    result = check_typosquatting("https://paypa1.com/login")
    assert result.triggered is True
    assert result.score_contribution >= 40
    assert result.metadata.get("closest_match") == "paypal.com"


def test_two_edit_typo_flagged_lower():
    # 'micrsft.com' = 2 deletions from 'microsoft.com'
    result = check_typosquatting("https://micrsft.com/")
    assert result.triggered is True
    assert result.score_contribution < 40  # 2-edit lands at score 25


def test_unrelated_domain_not_flagged():
    result = check_typosquatting("https://my-personal-blog-12345.dev/")
    assert result.triggered is False


def test_unparseable_url_handled():
    result = check_typosquatting("not-a-url")
    assert result.triggered is False
