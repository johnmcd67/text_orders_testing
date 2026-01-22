"""
Test suite for Spanish personal name fuzzy matching

Tests the specific case from Job 454 Order 1:
- Input: "MARIA ANTONIO BARROSO"
- Expected Match: "BARROSO MORALES MARIA ANTONIA" (Customer ID: 2522)
- Previous Score: 84% (below 85% threshold)
- Expected New Score: ≥85% (above threshold)
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.text_normalizer import (
    normalize_personal_name,
    is_personal_name,
    calculate_weighted_token_similarity
)
from rapidfuzz import fuzz


def test_personal_name_detection():
    """Test personal vs business name detection"""
    print("=" * 80)
    print("TEST 1: Personal vs Business Name Detection")
    print("=" * 80)
    print()

    test_cases = [
        # (input, expected_is_personal)
        ("maria antonio barroso", True),
        ("barroso morales maria antonia", True),
        ("materiales de construccion soria sl", False),
        ("distribuciones generalife maracena sl", False),
        ("jose garcia martinez", True),
        ("almacenes de construccion lito sl", False),
    ]

    all_passed = True
    for test_input, expected in test_cases:
        result = is_personal_name(test_input)
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"{status} '{test_input}'")
        print(f"       Expected: {expected}, Got: {result}")
        if result != expected:
            all_passed = False
        print()

    return all_passed


def test_personal_name_normalization():
    """Test personal name normalization (gendered names + token sorting)"""
    print("=" * 80)
    print("TEST 2: Personal Name Normalization")
    print("=" * 80)
    print()

    test_cases = [
        # Input 1: "MARIA ANTONIO BARROSO"
        # Note: "antonio" normalizes to "antonia" (min alphabetically)
        ("maria antonio barroso", "antonia barroso maria"),

        # Input 2: "BARROSO MORALES MARIA ANTONIA"
        # Both "antonio" and "antonia" normalize to "antonia"
        ("barroso morales maria antonia", "antonia barroso maria morales"),

        # Other cases
        # "francisco" normalizes to "francisca" (min alphabetically)
        ("francisco garcia lopez", "francisca garcia lopez"),
        ("lopez garcia francisca", "francisca garcia lopez"),
    ]

    all_passed = True
    for test_input, expected in test_cases:
        result = normalize_personal_name(test_input)
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"{status} Input:    '{test_input}'")
        print(f"       Expected: '{expected}'")
        print(f"       Got:      '{result}'")
        if result != expected:
            all_passed = False
        print()

    return all_passed


def test_job_454_case():
    """Test the specific failure case from Job 454 Order 1"""
    print("=" * 80)
    print("TEST 3: Job 454 Order 1 - MARIA ANTONIO BARROSO Case")
    print("=" * 80)
    print()

    # Input from email
    email_input = "MARIA ANTONIO BARROSO"

    # Correct customer in database
    db_name = "BARROSO MORALES MARIA ANTONIA"

    print("Input from Email:")
    print(f"  Original:   '{email_input}'")
    print()
    print("Database Customer:")
    print(f"  Original:   '{db_name}'")
    print()

    # Step 1: Normalize both names
    email_normalized = normalize_personal_name(email_input.lower())
    db_normalized = normalize_personal_name(db_name.lower())

    print("After Normalization:")
    print(f"  Email:      '{email_normalized}'")
    print(f"  Database:   '{db_normalized}'")
    print()

    # Step 2: Calculate base similarity
    base_score = fuzz.token_set_ratio(email_normalized, db_normalized) / 100.0

    print("Base Similarity Score (token_set_ratio):")
    print(f"  Score: {base_score:.4f} ({base_score * 100:.2f}%)")
    print()

    # Step 3: Apply weighted token scoring
    final_score = calculate_weighted_token_similarity(
        email_normalized,
        db_normalized,
        base_score
    )
    boost = final_score - base_score

    print("Weighted Token Scoring:")
    print(f"  Base:  {base_score:.4f}")
    print(f"  Boost: +{boost:.4f}")
    print(f"  Final: {final_score:.4f} ({final_score * 100:.2f}%)")
    print()

    # Step 4: Threshold check
    threshold = 0.85
    print(f"Threshold Check (85%):")
    print(f"  Threshold: {threshold:.4f} ({threshold * 100:.0f}%)")
    print(f"  Final Score: {final_score:.4f} ({final_score * 100:.2f}%)")

    if final_score >= threshold:
        print(f"  Status: [PASS] - Would match!")
        print()
        print("=" * 80)
        print("SUMMARY: [SUCCESS]")
        print("=" * 80)
        print(f"  Personal name normalization successfully improved matching:")
        print(f"  - Original score: 84% (below threshold)")
        print(f"  - New score: {final_score * 100:.2f}% (above threshold)")
        print(f"  - Improvement: +{(final_score - 0.84) * 100:.2f}%")
        print()
        return True
    else:
        print(f"  Status: [FAIL] - Would not match (short by {(threshold - final_score) * 100:.2f}%)")
        print()
        print("=" * 80)
        print("SUMMARY: [FAILED]")
        print("=" * 80)
        print(f"  Personal name normalization did not improve score enough.")
        print(f"  - New score: {final_score * 100:.2f}%")
        print(f"  - Needed: {threshold * 100:.0f}%")
        print(f"  - Shortfall: {(threshold - final_score) * 100:.2f}%")
        print()
        return False


if __name__ == "__main__":
    try:
        print("\n")
        print("=" * 80)
        print(" " * 15 + "SPANISH PERSONAL NAME FUZZY MATCHING TEST SUITE")
        print("=" * 80)
        print()

        # Run all tests
        test1_passed = test_personal_name_detection()
        test2_passed = test_personal_name_normalization()
        test3_passed = test_job_454_case()

        # Overall summary
        all_passed = test1_passed and test2_passed and test3_passed

        print()
        print("=" * 80)
        print("OVERALL TEST SUITE SUMMARY")
        print("=" * 80)
        print(f"Test 1 (Personal vs Business Detection): {'PASS' if test1_passed else 'FAIL'}")
        print(f"Test 2 (Personal Name Normalization):    {'PASS' if test2_passed else 'FAIL'}")
        print(f"Test 3 (Job 454 Case):                   {'PASS' if test3_passed else 'FAIL'}")
        print()

        if all_passed:
            print("[SUCCESS] All tests passed!")
            sys.exit(0)
        else:
            print("[FAILED] Some tests failed.")
            sys.exit(1)

    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
