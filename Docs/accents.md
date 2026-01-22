# Accent Normalization Fix for Customer Name Matching

## Problem

Fuzzy matching was failing when customer names contained accented characters (diacritics) because RapidFuzz treats accented and non-accented characters as different.

**Example:**
- Input from email: "FRAILE Y NUÑEZ S.L." (no accent on U)
- Database: "FRAILE Y NÚÑEZ" (accent on Ú)
- Match score: 0.79 (below 0.85 threshold) ❌

## Root Cause

The `fuzzy_match_customer()` function in `backend/utils/database.py` was comparing strings character-by-character after only applying `.lower().strip()`. This meant "u" and "ú" were treated as completely different characters, reducing the similarity score.

## Solution

Added accent normalization using Python's `unicodedata` module to strip diacritical marks before fuzzy matching. This ensures "ú" → "u", "ñ" → "n", "é" → "e", etc.

## Changes Made to `backend/utils/database.py`

### 1. Add Import

Add `unicodedata` to the imports at the top of the file:

```python
"""
PostgreSQL database utilities
"""
import os
import unicodedata  # <-- ADD THIS LINE
from typing import List, Tuple, Optional, Dict, Any
from rapidfuzz import fuzz
import psycopg
from .logger import logger
```

### 2. Add Helper Function

Add this function after the imports and before the `DatabaseHelper` class definition:

```python
def remove_accents(text: str) -> str:
    """
    Remove accents/diacritics from text for better fuzzy matching

    Examples:
        'FRAILE Y NÚÑEZ' -> 'FRAILE Y NUNEZ'
        'José María' -> 'Jose Maria'
        'Côte d'Azur' -> 'Cote d'Azur'

    Args:
        text: Input text with potential accents

    Returns:
        Text with accents removed
    """
    # Normalize to NFD (decompose characters into base + diacritics)
    nfd = unicodedata.normalize('NFD', text)
    # Filter out combining diacritical marks (category Mn)
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
```

### 3. Update Fuzzy Matching Logic

In the `fuzzy_match_customer()` method, update the nested loop that compares names:

**BEFORE:**
```python
# Try to match each potential name against all customers
for potential_name in potential_names:
    potential_name_lower = potential_name.lower().strip()

    for customer_id, db_customer_name in all_customers:
        db_name_lower = db_customer_name.lower().strip()

        # Calculate similarity score using token_set_ratio
        # This handles partial matches and word order differences well
        score = fuzz.token_set_ratio(potential_name_lower, db_name_lower) / 100.0
```

**AFTER:**
```python
# Try to match each potential name against all customers
for potential_name in potential_names:
    # Normalize: lowercase, strip whitespace, and remove accents
    potential_name_clean = remove_accents(potential_name.lower().strip())

    for customer_id, db_customer_name in all_customers:
        # Normalize: lowercase, strip whitespace, and remove accents
        db_name_clean = remove_accents(db_customer_name.lower().strip())

        # Calculate similarity score using token_set_ratio
        # This handles partial matches and word order differences well
        score = fuzz.token_set_ratio(potential_name_clean, db_name_clean) / 100.0
```

## How It Works

1. **Unicode NFD Normalization**: Decomposes characters into base character + combining diacritical mark
   - "ú" becomes "u" + " ́" (combining acute accent)
   - "ñ" becomes "n" + "~" (combining tilde)

2. **Filter Diacritical Marks**: Removes all characters in Unicode category "Mn" (Mark, nonspacing)
   - Keeps base character, discards the diacritical mark

3. **Fuzzy Match**: Compares normalized strings
   - "fraile y nunez s.l." vs "fraile y nunez"
   - Match score: ~95-100% ✅

## Testing

After applying these changes:

1. Restart the Celery worker to pick up the code changes
2. Process an order with accented customer names
3. Check logs for match scores - should now exceed 0.85 threshold

## Applying to Sister Codebases

This fix should be applied to:
- PDF Orders codebase (`pdf_orders/backend/utils/database.py`)
- Any other codebase that uses `fuzzy_match_customer()` function

The changes are identical - just follow the 3 steps above in the corresponding `database.py` file.

## Related Customer Names That Will Benefit

This fix helps with any customer names containing:
- Spanish characters: ñ, á, é, í, ó, ú
- French characters: é, è, ê, à, ô, ç
- Portuguese characters: ã, õ, â
- German characters: ä, ö, ü
- And many others across European languages

---

**Date Implemented**: 2025-11-24
**Files Modified**: `backend/utils/database.py`
**Issue**: Order 16 - FRAILE Y NUÑEZ S.L. failed to match (score 0.79)
