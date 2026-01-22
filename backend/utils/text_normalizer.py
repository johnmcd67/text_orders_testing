"""
Text Normalizer for Spanish Business Names

Provides normalization functions for Spanish business names to improve
fuzzy matching accuracy by handling synonyms, legal entity variations,
and buying group affiliations.
"""

import re
import unicodedata
from typing import List
from .spanish_business_synonyms import (
    BUSINESS_TYPE_SYNONYMS,
    COMPILED_LEGAL_ENTITY_PATTERNS,
    BUYING_GROUP_KEYWORDS
)


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


def normalize_business_name(text: str) -> str:
    """
    Normalize Spanish business name for fuzzy matching.

    Steps:
    1. Lowercase and remove accents
    2. Replace business type synonyms (word boundary matching)
    3. Normalize legal entity suffixes (regex)
    4. Remove commas and collapse whitespace

    Args:
        text: Business name to normalize

    Returns:
        Normalized business name

    Example:
        >>> normalize_business_name("Almacenes de Construcción Soria Gamma, S.L.")
        "materiales de construccion soria gamma sl"

        >>> normalize_business_name("MATERIALES DE CONSTRUCCION SORIA S.L.")
        "materiales de construccion soria sl"
    """
    try:
        # Step 1: Lowercase, remove accents, strip
        normalized = remove_accents(text.lower().strip())

        # Step 2: Apply business type synonyms (word boundary matching)
        for synonym_from, synonym_to in BUSINESS_TYPE_SYNONYMS.items():
            # Use word boundary to avoid partial word matches
            pattern = r'\b' + re.escape(synonym_from) + r'\b'
            normalized = re.sub(pattern, synonym_to, normalized, flags=re.IGNORECASE)

        # Step 3: Normalize legal entity suffixes
        for compiled_pattern, replacement in COMPILED_LEGAL_ENTITY_PATTERNS:
            normalized = compiled_pattern.sub(replacement, normalized)

        # Step 4: Remove commas and collapse spaces
        normalized = normalized.replace(',', ' ')
        normalized = re.sub(r'\s+', ' ', normalized)

        # Step 5: Strip again
        return normalized.strip()

    except Exception as e:
        # Fallback to original text if normalization fails
        # This ensures the system degrades gracefully
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Normalization failed for '{text}': {e}. Using original text.")
        return text.lower().strip()


def extract_buying_group_keywords(text: str) -> List[str]:
    """
    Extract buying group keywords from business name.

    Buying group keywords indicate membership in a purchasing consortium
    (e.g., "Gamma", "Gremio") and can be used to boost match scores.

    Args:
        text: Business name to analyze

    Returns:
        List of matched buying group keywords (lowercase)

    Example:
        >>> extract_buying_group_keywords("Almacenes Soria GRUPO GAMMA")
        ["grupo", "gamma"]

        >>> extract_buying_group_keywords("MATERIALES ABC")
        []
    """
    text_lower = text.lower()
    matched_keywords = []

    for keyword in BUYING_GROUP_KEYWORDS:
        # Use word boundary to avoid partial matches
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text_lower):
            matched_keywords.append(keyword)

    return matched_keywords


def calculate_boosted_similarity(
    normalized_text1: str,
    normalized_text2: str,
    keywords1: List[str],
    keywords2: List[str],
    base_score: float
) -> float:
    """
    Apply score boost if buying group keywords match.

    Boost rules:
    - +0.10 if any buying group keyword matches
    - +0.15 if multiple keywords match (2+)
    - Maximum boost: 0.15
    - Final score never exceeds 1.0

    Args:
        normalized_text1: First normalized business name
        normalized_text2: Second normalized business name
        keywords1: Buying group keywords from first name
        keywords2: Buying group keywords from second name
        base_score: Base similarity score (0.0 to 1.0)

    Returns:
        Boosted similarity score (0.0 to 1.0)

    Example:
        >>> calculate_boosted_similarity(
        ...     "materiales soria gamma sl",
        ...     "materiales soria sl",
        ...     ["gamma"],
        ...     ["grupo", "gamma"],
        ...     0.78
        ... )
        0.88  # 0.78 base + 0.10 boost for matching "gamma"
    """
    # If no keywords to compare, return base score
    if not keywords1 or not keywords2:
        return base_score

    # Find intersection of keywords (keywords that appear in both names)
    matched_keywords = set(keywords1) & set(keywords2)

    # No matching keywords, return base score
    if not matched_keywords:
        return base_score

    # Apply boost based on number of matched keywords
    if len(matched_keywords) == 1:
        boost = 0.10
    else:  # 2 or more matched keywords
        boost = 0.15

    # Calculate boosted score, capped at 1.0
    boosted_score = min(base_score + boost, 1.0)

    return boosted_score


def is_personal_name(text: str) -> bool:
    """
    Detect if a name is a personal name vs business name.

    Heuristic:
    1. No legal entity suffixes (SL, SA, SC, S.L., S.A., etc.)
    2. Token count ≤ 6 (most personal names are 2-4 words)
    3. No business keywords (MATERIALES, CONSTRUCCION, DISTRIBUIDOR, etc.)

    Args:
        text: Name to analyze (already normalized: lowercase, no accents)

    Returns:
        True if personal name, False if business name

    Examples:
        >>> is_personal_name("maria antonio barroso")
        True
        >>> is_personal_name("materiales de construccion soria sl")
        False
        >>> is_personal_name("barroso morales maria antonia")
        True
    """
    from .spanish_business_synonyms import BUSINESS_TYPE_SYNONYMS

    # Check 1: Legal entity suffix patterns
    legal_entity_patterns = [
        r'\bsl\b', r'\bsa\b', r'\bsc\b', r'\bs\.l\b', r'\bs\.a\b', r'\bs\.c\b',
        r'\bs\.l\.u\b', r'\bs\.l\.l\b', r'\bslu\b', r'\bsll\b',
    ]
    for pattern in legal_entity_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False  # Has legal entity suffix -> business name

    # Check 2: Token count (personal names typically 2-6 words)
    tokens = text.split()
    if len(tokens) > 6:
        return False  # Too many words -> likely business name

    # Check 3: Business keywords
    business_keywords = set(BUSINESS_TYPE_SYNONYMS.keys()) | set(BUSINESS_TYPE_SYNONYMS.values())
    business_keywords.update(["construccion", "materiales", "distribuidor", "comercio", "suministros"])

    text_lower = text.lower()
    for keyword in business_keywords:
        if keyword in text_lower:
            return False  # Has business keyword -> business name

    # If none of the above, likely a personal name
    return True


def normalize_personal_name(text: str) -> str:
    """
    Normalize Spanish personal name for fuzzy matching.

    Steps:
    1. Lowercase and remove accents (already done by caller)
    2. Normalize gendered name variants (ANTONIO <-> ANTONIA)
    3. Sort tokens alphabetically (handles word order variations)
    4. Remove duplicate tokens

    Args:
        text: Personal name to normalize (already lowercase, no accents)

    Returns:
        Normalized personal name with sorted tokens

    Examples:
        >>> normalize_personal_name("maria antonio barroso")
        "antonio barroso maria"

        >>> normalize_personal_name("barroso morales maria antonia")
        "antonio barroso maria morales"

        # After normalization, these two become closer:
        # Input 1: "antonio barroso maria" (sorted)
        # Input 2: "antonio barroso maria morales" (sorted)
        # token_set_ratio handles the missing "morales" gracefully
    """
    from .spanish_business_synonyms import SPANISH_GENDERED_NAMES

    try:
        # Step 1: Tokenize
        tokens = text.split()

        # Step 2: Normalize gendered names
        normalized_tokens = []
        for token in tokens:
            # If token is a gendered name, normalize to its pair
            # This makes ANTONIO and ANTONIA equivalent
            if token in SPANISH_GENDERED_NAMES:
                # Always normalize to alphabetically first variant
                variant = SPANISH_GENDERED_NAMES[token]
                normalized_token = min(token, variant)  # e.g., min("antonio", "antonia") = "antonio"
                normalized_tokens.append(normalized_token)
            else:
                normalized_tokens.append(token)

        # Step 3: Sort tokens alphabetically
        # This handles word order: "MARIA ANTONIO BARROSO" and "BARROSO MARIA ANTONIO" -> same
        normalized_tokens.sort()

        # Step 4: Remove duplicates (preserve order after sort)
        seen = set()
        unique_tokens = []
        for token in normalized_tokens:
            if token not in seen:
                seen.add(token)
                unique_tokens.append(token)

        # Step 5: Join back to string
        return " ".join(unique_tokens)

    except Exception as e:
        # Fallback to original text if normalization fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Personal name normalization failed for '{text}': {e}. Using original text.")
        return text


def calculate_jaro_winkler_similarity(text1: str, text2: str, prefix_weight: float = 0.15) -> float:
    """
    Calculate Jaro-Winkler similarity between two strings.

    Jaro-Winkler gives extra weight to prefix matches, making it ideal
    for detecting abbreviations (FAMICAS → FAMICAST) and typos.

    This is used as a complementary algorithm to token_set_ratio:
    - token_set_ratio excels at word order variations
    - Jaro-Winkler excels at character-level similarity

    Args:
        text1: First normalized string
        text2: Second normalized string
        prefix_weight: Weight given to matching prefix (default 0.15)

    Returns:
        Similarity score (0.0 to 1.0)

    Example:
        >>> calculate_jaro_winkler_similarity("famicas", "famicast sl")
        0.87  # High score despite missing 'T' - prefix match boosted
    """
    from rapidfuzz.distance import JaroWinkler
    return JaroWinkler.normalized_similarity(text1, text2, prefix_weight=prefix_weight)


def calculate_weighted_token_similarity(
    text1: str,
    text2: str,
    base_score: float
) -> float:
    """
    Calculate weighted token similarity for personal names.

    Down-weights common given names (MARIA, JOSE) and up-weights surnames.
    This helps prioritize surname matches over given name matches.

    Args:
        text1: First normalized personal name
        text2: Second normalized personal name
        base_score: Base similarity score from token_set_ratio

    Returns:
        Adjusted similarity score (can be slightly higher or lower than base)

    Example:
        >>> calculate_weighted_token_similarity(
        ...     "antonio barroso maria",
        ...     "antonio barroso maria morales",
        ...     0.84
        ... )
        0.87  # Slight boost for surname "barroso" match
    """
    from .spanish_business_synonyms import (
        COMMON_SPANISH_GIVEN_NAMES,
        COMMON_SPANISH_SURNAMES
    )

    # Tokenize both names
    tokens1 = set(text1.split())
    tokens2 = set(text2.split())

    # Find common tokens
    common_tokens = tokens1 & tokens2

    if not common_tokens:
        return base_score  # No common tokens, return base score

    # Calculate weighted bonus
    surname_matches = sum(1 for token in common_tokens if token in COMMON_SPANISH_SURNAMES)
    given_name_matches = sum(1 for token in common_tokens if token in COMMON_SPANISH_GIVEN_NAMES)

    # Boost for surname matches (+0.03 per surname match, max +0.06)
    # Penalty for only given name matches (-0.02 per given name if no surnames match)
    surname_boost = min(surname_matches * 0.03, 0.06)

    if surname_matches > 0:
        # Has surname match -> apply boost
        final_score = min(base_score + surname_boost, 1.0)
    elif given_name_matches > 0:
        # Only given name matches, no surnames -> slight penalty
        given_name_penalty = min(given_name_matches * 0.02, 0.04)
        final_score = max(base_score - given_name_penalty, 0.0)
    else:
        # Neither surnames nor common given names -> neutral
        final_score = base_score

    return final_score
