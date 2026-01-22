"""
Subagent 2: SKU & Quantity Extraction
Extracts product SKU and quantity from email
SKU format: Family (3 chars) + Length (3 digits) + Width (3 digits) + Color (4 chars) = 13 chars
"""
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from difflib import SequenceMatcher
from backend.utils.anthropic_helper import get_anthropic_helper
from backend.utils.database import get_db_helper
from backend.utils.logger import logger


# Color synonyms/aliases mapping
# Maps common color descriptions to their canonical database names
COLOR_SYNONYMS = {
    "gris claro": "gris perla",      # Light grey -> Pearl grey (7035)
    "gris clara": "gris perla",      # Feminine form
    "gris light": "gris perla",      # English variant
    "light grey": "gris perla",      # English
    "light gray": "gris perla",      # US English
    "gris oscuro": "gris",           # Dark grey -> Standard grey (7037)
    "gris oscura": "gris",           # Feminine form
    "dark grey": "gris",             # English
    "dark gray": "gris",             # US English
}


def load_prompt_template() -> str:
    """Load the SKU extraction prompt template"""
    prompt_file = Path(__file__).parent.parent / "prompts" / "sku_extraction.txt"
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()


def fuzzy_match_family(family_text: str, families: List[tuple], threshold: float = 0.6) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """
    Fuzzy match family name against database families

    Args:
        family_text: Family name from email
        families: List of (family_desc, 13DigitPrefix) tuples from database
        threshold: Minimum similarity score

    Returns:
        Tuple of (family_prefix, family_desc, match_details) where match_details contains:
        - best_score: float
        - closest_family: str
        - threshold_used: float
        - input_text: str
    """
    family_text_lower = family_text.lower().strip()
    best_score = 0.0
    best_prefix = None
    best_family_desc = None

    for family_desc, prefix in families:
        family_desc_lower = family_desc.lower().strip()
        score = SequenceMatcher(None, family_text_lower, family_desc_lower).ratio()

        if score > best_score:
            best_score = score
            best_prefix = prefix
            best_family_desc = family_desc

    match_details = {
        "best_score": best_score,
        "closest_family": best_family_desc,
        "threshold_used": threshold,
        "input_text": family_text
    }

    if best_score >= threshold:
        logger.debug(f"Family match: '{family_text}' -> '{best_prefix}' ({best_family_desc}, score: {best_score:.2f})")
        return best_prefix, best_family_desc, match_details
    else:
        logger.warning(f"No family match for: '{family_text}' (best score: {best_score:.2f})")
        return None, None, match_details


def fuzzy_match_color(color_text: str, colors: List[tuple], threshold: float = 0.6) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Fuzzy match color name against database colors

    Args:
        color_text: Color name from email
        colors: List of (color_description, colorcode) tuples from database
        threshold: Minimum similarity score

    Returns:
        Tuple of (color_code, match_details) where match_details contains:
        - best_score: float
        - closest_color: str
        - threshold_used: float
        - input_text: str
    """
    color_text_lower = color_text.lower().strip()
    original_color_text = color_text_lower  # Keep original for logging

    # Check for known color synonyms first
    if color_text_lower in COLOR_SYNONYMS:
        canonical_color = COLOR_SYNONYMS[color_text_lower]
        logger.info(f"Color synonym mapping: '{color_text}' -> '{canonical_color}'")
        color_text_lower = canonical_color

    best_score = 0.0
    best_code = None
    best_color_desc = None

    for color_desc, colorcode in colors:
        color_desc_lower = color_desc.lower().strip()
        score = SequenceMatcher(None, color_text_lower, color_desc_lower).ratio()

        if score > best_score:
            best_score = score
            best_code = colorcode
            best_color_desc = color_desc

    match_details = {
        "best_score": best_score,
        "closest_color": best_color_desc,
        "threshold_used": threshold,
        "input_text": color_text
    }

    if best_score >= threshold:
        logger.debug(f"Color match: '{color_text}' -> '{best_code}' (score: {best_score:.2f})")
        return best_code, match_details
    else:
        logger.warning(f"No color match for: '{color_text}' (best score: {best_score:.2f})")
        return None, match_details


def construct_sku(family_prefix: str, length: int, width: int, color_code: str) -> str:
    """
    Construct 13-character SKU

    Args:
        family_prefix: 3-character family code
        length: Length in cm (larger dimension)
        width: Width in cm (smaller dimension)
        color_code: 4-character color code

    Returns:
        13-character SKU string
    """
    # Ensure length > width (swap if needed)
    if width > length:
        length, width = width, length
        logger.debug(f"Swapped dimensions: length={length}, width={width}")

    # Zero-pad to 3 digits
    length_str = str(length).zfill(3)
    width_str = str(width).zfill(3)

    # Construct SKU
    sku = f"{family_prefix}{length_str}{width_str}{color_code}"

    if len(sku) != 13:
        logger.error(f"Invalid SKU length: {sku} (length={len(sku)}, expected=13)")
        return None

    return sku


def extract_sku_and_quantity(email_text: str) -> Dict[str, any]:
    """
    Extract SKU and quantity from email text

    Process:
    1. Get product families and color codes from database
    2. Use gpt-4o-mini to extract product info (family, dimensions, color, qty)
    3. Fuzzy match family and color against database
    4. Construct 13-character SKU for each order line
    5. Return list of order lines with SKU and quantity

    Args:
        email_text: Raw email content (cleaned)

    Returns:
        Dictionary with:
        - order_lines (list): List of dicts with 'sku' and 'quantity'
        - error (str or None): Error message if extraction failed
        - failure_context (dict or None): Detailed context when extraction fails
    """
    logger.info("Subagent 2: Starting SKU & quantity extraction")

    try:
        # Step 1: Get product families and colors from database
        db_helper = get_db_helper()
        families = db_helper.get_product_families()
        colors = db_helper.get_color_codes()

        logger.info(f"Retrieved {len(families)} families and {len(colors)} colors from database")

        # Format lists for prompt
        families_list = "\n".join([f"- {desc}" for desc, _ in families])
        colors_list = "\n".join([f"- {desc}" for desc, _ in colors])

        # Step 2: Load prompt template
        prompt_template = load_prompt_template()
        prompt = prompt_template.format(
            email_text=email_text,
            families_list=families_list,
            colors_list=colors_list
        )

        # Step 3: Call Claude to extract product info
        anthropic_helper = get_anthropic_helper()
        response = anthropic_helper.call_default(prompt=prompt)

        order_lines_raw = response.get("order_lines", [])
        logger.info(f"LLM extracted {len(order_lines_raw)} order lines")

        if not order_lines_raw:
            logger.warning("No order lines found in email")
            return {
                "order_lines": [],
                "error": "No order lines found in email",
                "failure_context": {
                    "type": "sku_extraction",
                    "reason": "no_order_lines",
                    "email_snippet": email_text[:500] if email_text else None
                }
            }

        # Step 4: Process each order line
        order_lines_processed = []
        failed_lines = []  # Track failed lines with context

        for idx, line in enumerate(order_lines_raw, 1):
            logger.info(f"Processing order line {idx}: {line}")

            # Extract fields
            family_text = line.get("family", "")
            length = line.get("length")
            width = line.get("width")
            color_text = line.get("color", "")
            quantity = line.get("quantity")

            # Validate fields
            if not all([family_text, length, width, color_text, quantity]):
                logger.error(f"Missing required fields in order line {idx}: {line}")
                failed_lines.append({
                    "line_number": idx,
                    "reason": "missing_fields",
                    "raw_line": line
                })
                continue

            # Fuzzy match family
            family_prefix, family_desc, family_match_details = fuzzy_match_family(family_text, families)
            if not family_prefix:
                logger.error(f"Could not match family: {family_text}")
                failed_lines.append({
                    "line_number": idx,
                    "reason": "family_match_failed",
                    "extracted_family": family_text,
                    "family_match_score": family_match_details.get("best_score"),
                    "closest_family": family_match_details.get("closest_family"),
                    "raw_line": line
                })
                continue

            # Check if color is already a RAL code (4-digit number) - use directly
            if color_text and str(color_text).isdigit() and len(str(color_text)) == 4:
                color_code = str(color_text)
                color_match_details = {"best_score": 1.0, "closest_color": color_text, "input_text": color_text}
                logger.info(f"Using RAL code directly: {color_code}")
            else:
                # Fuzzy match color against database descriptions
                color_code, color_match_details = fuzzy_match_color(color_text, colors)
                if not color_code:
                    logger.error(f"Could not match color: {color_text}")
                    failed_lines.append({
                        "line_number": idx,
                        "reason": "color_match_failed",
                        "extracted_color": color_text,
                        "color_match_score": color_match_details.get("best_score"),
                        "closest_color": color_match_details.get("closest_color"),
                        "raw_line": line
                    })
                    continue

            # Construct SKU
            sku = construct_sku(family_prefix, length, width, color_code)
            if not sku:
                logger.error(f"Failed to construct SKU for line {idx}")
                failed_lines.append({
                    "line_number": idx,
                    "reason": "sku_construction_failed",
                    "family_prefix": family_prefix,
                    "length": length,
                    "width": width,
                    "color_code": color_code,
                    "raw_line": line
                })
                continue

            # Add to processed list
            order_lines_processed.append({
                "sku": sku,
                "quantity": quantity,
                "family_desc": family_desc
            })

            logger.info(f"Order line {idx} processed: SKU={sku}, Qty={quantity}")

        # Step 5: Return results
        if not order_lines_processed:
            logger.error("No order lines could be processed successfully")
            # Build detailed failure context from failed lines
            failure_context = {
                "type": "sku_extraction",
                "reason": "all_lines_failed",
                "total_lines_attempted": len(order_lines_raw),
                "failed_lines": failed_lines,
                "email_snippet": email_text[:500] if email_text else None
            }
            return {
                "order_lines": [],
                "error": "Failed to process any order lines",
                "failure_context": failure_context
            }

        logger.info(f"SKU extraction successful: {len(order_lines_processed)} order lines")
        return {
            "order_lines": order_lines_processed,
            "error": None,
            "failure_context": None
        }

    except Exception as e:
        logger.error(f"Subagent 2 failed: {e}", exc_info=True)
        return {
            "order_lines": [],
            "error": str(e),
            "failure_context": {
                "type": "sku_extraction",
                "reason": "exception",
                "exception_message": str(e),
                "email_snippet": email_text[:500] if email_text else None
            }
        }


# Convenience function for testing
def test_subagent():
    """Test the subagent with sample email"""
    sample_email = """
    Te indico pedido:
    1 plato ducha nature 140x80 BLANCO
    1 plato ducha nature 150x80 BLANCO
    1 plato ducha nature 130x80 BLANCO

    saludos
    """

    result = extract_sku_and_quantity(sample_email)
    print("\n=== Subagent 2 Test Result ===")
    print(f"Order Lines: {len(result['order_lines'])}")
    for idx, line in enumerate(result['order_lines'], 1):
        print(f"  Line {idx}: SKU={line['sku']}, Qty={line['quantity']}")
    print(f"Error: {result['error']}")
    print("==============================\n")

    return result


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Run test
    test_subagent()

