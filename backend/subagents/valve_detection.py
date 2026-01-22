"""
Subagent 4: Valve Detection
Detects if customer has requested an ALTERNATIVE/UPGRADED valve type per order line.

Business Logic:
- "no" = Standard horizontal valve (default) - customer just wants valve included
- "Yes" = Alternative valve requested but type not specified (rare)
- Specific types (Vertical, Horizontal, Rectangular) = Explicit alternative valve request
"""
from pathlib import Path
from typing import Dict, List
from backend.utils.anthropic_helper import get_anthropic_helper
from backend.utils.logger import logger

# Valid valve values that can be returned
VALID_VALVE_VALUES = {"Yes", "no", "Horizontal valve", "Vertical valve", "Rectangular valve"}


def load_prompt_template() -> str:
    """Load the valve detection prompt template"""
    prompt_file = Path(__file__).parent.parent / "prompts" / "valve_detection.txt"
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()


def detect_valve_request(email_text: str, num_order_lines: int = 1) -> Dict[str, any]:
    """
    Detect if customer has requested a valve and assign valve types to order lines

    Args:
        email_text: Raw email content (cleaned)
        num_order_lines: Number of order lines extracted from the email

    Returns:
        Dictionary with:
        - valves (list[str]): Array of valve assignments per order line
          Valid values: "Yes", "no", "Horizontal valve", "Vertical valve", "Rectangular valve"
        - error (str or None): Error message if detection failed
    """
    logger.info(f"Subagent 4: Starting valve detection for {num_order_lines} order line(s)")

    try:
        # Load prompt template
        prompt_template = load_prompt_template()
        prompt = prompt_template.format(
            email_text=email_text,
            num_order_lines=num_order_lines
        )

        # Call Claude to detect valve request
        anthropic_helper = get_anthropic_helper()
        response = anthropic_helper.call_default(prompt=prompt)

        # Extract valves array from response
        valves = response.get("valves", [])

        # Ensure valves is a list
        if not isinstance(valves, list):
            logger.warning(f"Valve response is not a list: {valves}")
            valves = ["no"] * num_order_lines

        # Validate array length matches order lines
        if len(valves) != num_order_lines:
            logger.warning(f"Valve array length mismatch: got {len(valves)}, expected {num_order_lines}")
            # Pad with "no" if too short, truncate if too long
            if len(valves) < num_order_lines:
                valves.extend(["no"] * (num_order_lines - len(valves)))
            else:
                valves = valves[:num_order_lines]

        # Validate each value is in allowed set (default to "no" if invalid)
        valves = [v if v in VALID_VALVE_VALUES else "no" for v in valves]

        logger.info(f"Valve detection result: {valves}")

        return {
            "valves": valves,
            "error": None
        }

    except Exception as e:
        logger.error(f"Subagent 4 failed: {e}", exc_info=True)
        # Default: all "no" on error
        return {
            "valves": ["no"] * num_order_lines,
            "error": str(e)
        }


# Convenience function for testing
def test_subagent():
    """Test the subagent with sample emails"""

    # Test 1: No valve (3 order lines)
    sample_email_1 = """
    Te indico pedido:
    1 plato ducha nature 140x80 BLANCO
    1 plato ducha nature 120x70 BLANCO
    1 plato ducha nature 100x80 BLANCO
    saludos
    """

    # Test 2: Red herring (1 order line) - válvula de Tecnoagua should be ignored
    sample_email_2 = """
    1 plato ducha nature 140x80 BLANCO c/válv
    válvula de Tecnoagua
    """

    # Test 3: Standard valve request (2 order lines) - "con válvula" is standard, NOT alternative
    sample_email_3 = """
    2 platos ducha nature 140x80 BLANCO
    Con válvula
    """

    # Test 4: Specific valve types (3 order lines) - "2 laterales y 1 vertical"
    sample_email_4 = """
    3 PLATOS NATURE 140x80 BLANCO
    Si puede ser 2 valvulas laterales y 1 vertical
    """

    # Test 5: Single vertical valve (3 order lines)
    sample_email_5 = """
    3 platos ducha nature 140x80 BLANCO
    1 válvula vertical
    """

    # Test 6: "+ válvula" standard valve request (1 order line) - like job 575
    sample_email_6 = """
    1 plato PREMIUM 160x80 blanco + válvula
    """

    print("\n=== Subagent 4 Test 1 (No valve, 3 lines) ===")
    result1 = detect_valve_request(sample_email_1, num_order_lines=3)
    print(f"Valves: {result1['valves']}")
    print(f"Expected: ['no', 'no', 'no']")
    print(f"Error: {result1['error']}")

    print("\n=== Subagent 4 Test 2 (Red herring, 1 line) ===")
    result2 = detect_valve_request(sample_email_2, num_order_lines=1)
    print(f"Valves: {result2['valves']}")
    print(f"Expected: ['no']")
    print(f"Error: {result2['error']}")

    print("\n=== Subagent 4 Test 3 (Standard valve 'con válvula', 2 lines) ===")
    result3 = detect_valve_request(sample_email_3, num_order_lines=2)
    print(f"Valves: {result3['valves']}")
    print(f"Expected: ['no', 'no']")  # Standard valve = "no" (not alternative)
    print(f"Error: {result3['error']}")

    print("\n=== Subagent 4 Test 4 (2 laterales y 1 vertical, 3 lines) ===")
    result4 = detect_valve_request(sample_email_4, num_order_lines=3)
    print(f"Valves: {result4['valves']}")
    print(f"Expected: ['Horizontal valve', 'Horizontal valve', 'Vertical valve']")
    print(f"Error: {result4['error']}")

    print("\n=== Subagent 4 Test 5 (1 vertical, 3 lines) ===")
    result5 = detect_valve_request(sample_email_5, num_order_lines=3)
    print(f"Valves: {result5['valves']}")
    print(f"Expected: ['Vertical valve', 'no', 'no']")
    print(f"Error: {result5['error']}")

    print("\n=== Subagent 4 Test 6 ('+ válvula' standard valve, 1 line) ===")
    result6 = detect_valve_request(sample_email_6, num_order_lines=1)
    print(f"Valves: {result6['valves']}")
    print(f"Expected: ['no']")  # Standard valve inclusion = "no"
    print(f"Error: {result6['error']}")

    print("==============================\n")

    return result1, result2, result3, result4, result5, result6


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Run test
    test_subagent()
