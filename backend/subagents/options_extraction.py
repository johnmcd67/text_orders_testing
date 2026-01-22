"""
Subagent 8: Options Extraction
Extracts option SKU and quantity (rejillas/grids or cubrir/covers) from email
"""
from pathlib import Path
from typing import Dict, List, Optional
from difflib import SequenceMatcher
from backend.utils.anthropic_helper import get_anthropic_helper
from backend.utils.database import get_db_helper
from backend.utils.logger import logger


def load_prompt_template() -> str:
    """Load the options extraction prompt template"""
    prompt_file = Path(__file__).parent.parent / "prompts" / "options_extraction.txt"
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()


def fuzzy_match_color(color_text: str, colors: List[tuple], threshold: float = 0.6) -> Optional[str]:
    """
    Fuzzy match color name against database colors

    Args:
        color_text: Color name from email
        colors: List of (color_description, colorcode) tuples from database
        threshold: Minimum similarity score

    Returns:
        4-character color code or None
    """
    color_text_lower = color_text.lower().strip()
    best_score = 0.0
    best_code = None

    for color_desc, colorcode in colors:
        color_desc_lower = color_desc.lower().strip()
        score = SequenceMatcher(None, color_text_lower, color_desc_lower).ratio()

        if score > best_score:
            best_score = score
            best_code = colorcode

    if best_score >= threshold:
        logger.debug(f"Color match: '{color_text}' -> '{best_code}' (score: {best_score:.2f})")
        return best_code
    else:
        logger.warning(f"No color match for: '{color_text}' (best score: {best_score:.2f})")
        return None


def extract_options(email_text: str, order_lines: List[Dict]) -> Dict[str, any]:
    """
    Extract option SKU and quantity from email text

    Process:
    1. Use LLM to detect if options (rejillas/cubrir) are mentioned
    2. If yes, extract color, quantity (and size/type for Premium)
    3. Get family from order_lines (use first line's family)
    4. Fuzzy match color against database
    5. Query public.optionstable using family-specific logic
    6. Return option_sku and option_qty

    Args:
        email_text: Raw email content (cleaned)
        order_lines: List of order line dicts with 'sku', 'quantity', 'family_desc'

    Returns:
        Dictionary with:
        - option_sku (str or None): Option SKU if found
        - option_qty (int or None): Option quantity if found
        - error (str or None): Error message if extraction failed
    """
    logger.info("Subagent 8: Starting options extraction")

    try:
        # Check if we have order lines (need family info)
        if not order_lines or len(order_lines) == 0:
            logger.warning("No order lines provided - cannot determine family")
            return {
                "option_sku": None,
                "option_qty": None,
                "error": None
            }

        # Get family from first order line
        family_desc = order_lines[0].get("family_desc")
        if not family_desc:
            logger.warning("No family_desc in order lines")
            return {
                "option_sku": None,
                "option_qty": None,
                "error": None
            }

        logger.info(f"Using family from order lines: {family_desc}")

        # Step 1: Get color codes from database
        db_helper = get_db_helper()
        colors = db_helper.get_color_codes()
        logger.info(f"Retrieved {len(colors)} colors from database")

        # Format colors list for prompt
        colors_list = "\n".join([f"- {desc}" for desc, _ in colors])

        # Step 2: Load prompt template
        prompt_template = load_prompt_template()
        prompt = prompt_template.format(
            email_text=email_text,
            colors_list=colors_list
        )

        # Step 3: Call LLM to detect options
        anthropic_helper = get_anthropic_helper()
        response = anthropic_helper.call_default(prompt=prompt)

        has_options = response.get("has_options", False)

        # If no options, return None
        if not has_options:
            logger.info("No options found in email")
            return {
                "option_sku": None,
                "option_qty": None,
                "error": None
            }

        # Step 4: Extract option details
        color_text = response.get("color", "")
        quantity = response.get("quantity", 1)
        size = response.get("size")  # For Premium only
        option_type = response.get("type")  # For Premium only

        logger.info(f"Options detected: color={color_text}, quantity={quantity}, size={size}, type={option_type}")

        # Step 5: Fuzzy match color
        color_code = None
        if color_text:
            color_code = fuzzy_match_color(color_text, colors)
            if not color_code:
                logger.warning(f"Could not match color: {color_text}")

        # Step 6: Query optionstable with family-specific logic
        option_sku = db_helper.query_options_table(
            family=family_desc,
            color_code=color_code,
            size=size,
            option_type=option_type
        )

        if not option_sku:
            logger.warning(f"No option SKU found for family={family_desc}, color={color_code}")
            return {
                "option_sku": None,
                "option_qty": None,
                "error": f"No option SKU found for family {family_desc}"
            }

        logger.info(f"Options extraction successful: SKU={option_sku}, Qty={quantity}")
        return {
            "option_sku": option_sku,
            "option_qty": quantity,
            "error": None
        }

    except Exception as e:
        logger.error(f"Subagent 8 failed: {e}", exc_info=True)
        return {
            "option_sku": None,
            "option_qty": None,
            "error": str(e)
        }


# Convenience function for testing
def test_subagent():
    """Test the subagent with sample emails"""

    # Test 1: Email with options (Nature family) - Real email with MOKA
    sample_email_1 = """
    Hola, os paso para servirnos
    1 plato nature 170*110 moka 1001 con rejilla mismo color moka
    Ref. Arantxa
    """
    sample_order_lines_1 = [
        {"sku": "NAT170110MOKA", "quantity": 1, "family_desc": "Nature"}
    ]

    # Test 2: Email without options
    sample_email_2 = """
    Te indico pedido:
    1 plato ducha hermes 160x80 BEIGE

    saludos
    """
    sample_order_lines_2 = [
        {"sku": "HER160080BEIG", "quantity": 1, "family_desc": "Hermes"}
    ]

    # Test 3: Email with Premium options (size and type)
    sample_email_3 = """
    1 plato ducha premium 80x80 BLANCO
    1 grid 80
    """
    sample_order_lines_3 = [
        {"sku": "PRE080080BLCO", "quantity": 1, "family_desc": "Premium"}
    ]

    print("\n=== Subagent 8 Test 1 (Nature with rejilla MOKA) ===")
    result1 = extract_options(sample_email_1, sample_order_lines_1)
    print(f"Option SKU: {result1['option_sku']}")
    print(f"Option Qty: {result1['option_qty']}")
    print(f"Error: {result1['error']}")

    print("\n=== Subagent 8 Test 2 (Hermes without options) ===")
    result2 = extract_options(sample_email_2, sample_order_lines_2)
    print(f"Option SKU: {result2['option_sku']}")
    print(f"Option Qty: {result2['option_qty']}")
    print(f"Error: {result2['error']}")

    print("\n=== Subagent 8 Test 3 (Premium with grid 80) ===")
    result3 = extract_options(sample_email_3, sample_order_lines_3)
    print(f"Option SKU: {result3['option_sku']}")
    print(f"Option Qty: {result3['option_qty']}")
    print(f"Error: {result3['error']}")
    print("==============================\n")

    return result1, result2, result3


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Run test
    test_subagent()

