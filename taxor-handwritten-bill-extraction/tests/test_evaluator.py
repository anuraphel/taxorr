import pytest
from evaluator.evaluator import fuzzy_ratio, normalize_date, is_field_correct

def test_fuzzy_ratio():
    # Exact match
    assert fuzzy_ratio("Sharma Kirana Store", "Sharma Kirana Store") == 1.0
    # Small differences (spaces, casing, punctuation)
    assert fuzzy_ratio("Sharma Kirana Store", "sharma kirana store") == 1.0
    assert fuzzy_ratio("Pooja Medicals", "Pooja Medical") >= 0.85
    # Substantially different
    assert fuzzy_ratio("Sharma Kirana Store", "Gupta Sweets") < 0.5
    # Empty string edge cases
    assert fuzzy_ratio("", "") == 1.0
    assert fuzzy_ratio("ABC", "") == 0.0

def test_normalize_date():
    # Standard YYYY-MM-DD
    assert normalize_date("2026-07-12") == "2026-07-12"
    # DD/MM/YYYY
    assert normalize_date("14/07/2026") == "2026-07-14"
    # DD-MM-YYYY
    assert normalize_date("14-07-2026") == "2026-07-14"
    # Textual DD-Month-YYYY
    assert normalize_date("18-July-2026") == "2026-07-18"
    assert normalize_date("18 July 2026") == "2026-07-18"
    # Textual Month DD YYYY
    assert normalize_date("July 18 2026") == "2026-07-18"
    # N/A case
    assert normalize_date("N/A") == "N/A"
    assert normalize_date("na") == "N/A"

def test_is_field_correct():
    # Amount exact and small float offset
    correct, score = is_field_correct("amount", 650.00, 650)
    assert correct and score == 1.0
    
    correct, score = is_field_correct("amount", 650.04, 650.00)
    assert correct and score == 1.0
    
    correct, score = is_field_correct("amount", 650.10, 650.00)
    assert not correct and score == 0.0
    
    # Date formatting mismatch but same value
    correct, score = is_field_correct("date", "14/07/2026", "2026-07-14")
    assert correct and score == 1.0
    
    # Text values with minor spelling errors
    correct, score = is_field_correct("vendor_name", "Pooja Medical", "Pooja Medicals")
    assert correct and score >= 0.80
