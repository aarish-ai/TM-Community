"""Tests for GDELT query sanitizer."""

import pytest
from truth_mirror.retrieval_news import sanitize_gdelt_query


def test_empty_or_short_queries():
    assert sanitize_gdelt_query("") == ""
    assert sanitize_gdelt_query("   ") == ""
    assert sanitize_gdelt_query("a") == ""
    assert sanitize_gdelt_query("to") == ""
    assert sanitize_gdelt_query("in at") == ""
    assert sanitize_gdelt_query("!?#") == ""


def test_acronym_expansion():
    assert "United States" in sanitize_gdelt_query("us economy")
    assert "United Kingdom" in sanitize_gdelt_query("UK election")
    assert "European Union" in sanitize_gdelt_query("EU trade agreement")
    assert "United Nations" in sanitize_gdelt_query("UN summit")
    assert "Associated Press" in sanitize_gdelt_query("AP report")
    assert "Artificial Intelligence" in sanitize_gdelt_query("ai safety laws")


def test_punctuation_and_quotes_stripping():
    result = sanitize_gdelt_query("claim: 'mars rover found water!'")
    assert ":" not in result
    assert "'" not in result
    assert "!" not in result
    assert "claim" in result
    assert "mars" in result
    assert "rover" in result
    assert "found" in result
    assert "water" in result


def test_url_stripping():
    result = sanitize_gdelt_query("breaking news https://example.com/article?id=123 update")
    assert "http" not in result
    assert "example.com" not in result
    assert "breaking" in result
    assert "news" in result
    assert "update" in result


def test_short_token_filtering():
    # Words < 3 chars that are not recognized acronyms should be filtered out
    # "is", "on", "in", "to", "20" removed, but words >= 3 retained
    result = sanitize_gdelt_query("is the president on trip in 20 to paris")
    tokens = result.split()
    assert "is" not in tokens
    assert "on" not in tokens
    assert "in" not in tokens
    assert "20" not in tokens
    assert "to" not in tokens
    assert "the" in tokens
    assert "president" in tokens
    assert "trip" in tokens
    assert "paris" in tokens


def test_long_query_truncation():
    long_query = "climate change environmental policy renewable energy solar wind nuclear power greenhouse gas emissions reduction target international agreement global warming " * 5
    result = sanitize_gdelt_query(long_query)
    assert len(result) <= 250
    assert len(result) > 0
