"""
Subagent 3: Reference Number Extraction
Extracts reference number from email, with special rule for customer 2693
"""
from pathlib import Path
from typing import Dict, Optional
from backend.utils.anthropic_helper import get_anthropic_helper
from backend.utils.logger import logger


def load_prompt_template() -> str:
    """Load the reference number prompt template"""
    prompt_file = Path(__file__).parent.parent / "prompts" / "reference_no.txt"
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()


def extract_reference_no(email_text: str, customer_id: int) -> Dict[str, Optional[list]]:
    """
    Extract reference numbers from email text

    Args:
        email_text: Raw email content (cleaned)
        customer_id: Customer ID (for special rules)

    Returns:
        Dictionary with:
        - reference_nos (list): List of reference numbers (one per order line), empty list if none found
        - error (str or None): Error message if extraction failed
    """
    logger.info(f"Subagent 3: Starting reference number extraction (customer_id={customer_id})")

    try:
        # Load prompt template
        prompt_template = load_prompt_template()
        prompt = prompt_template.format(
            email_text=email_text,
            customer_id=customer_id
        )

        # Call Claude (reference extraction is straightforward)
        anthropic_helper = get_anthropic_helper()
        response = anthropic_helper.call_default(prompt=prompt)

        reference_nos = response.get("reference_nos", [])

        if reference_nos:
            logger.info(f"Reference numbers extracted: {reference_nos}")
        else:
            logger.info("No reference numbers found in email")

        return {
            "reference_nos": reference_nos,
            "error": None
        }

    except Exception as e:
        logger.error(f"Subagent 3 failed: {e}", exc_info=True)
        return {
            "reference_nos": [],
            "error": str(e)
        }


# Convenience function for testing
def test_subagent():
    """Test the subagent with sample emails"""

    # Test 1: No reference number
    sample_email_1 = """
    Te indico pedido:
    1 plato ducha nature 140x80 BLANCO
    saludos
    """

    # Test 2: Customer 2693 with special pattern
    sample_email_2 = """
    Por favor, tramitad el siguiente pedido Nº 173082 DADIVASTUDIO SL
    1 plato ducha nature 140x80 BLANCO
    """

    print("\n=== Subagent 3 Test 1 (No ref) ===")
    result1 = extract_reference_no(sample_email_1, customer_id=1234)
    print(f"Reference Nos: {result1['reference_nos']}")
    print(f"Error: {result1['error']}")

    print("\n=== Subagent 3 Test 2 (Customer 2693) ===")
    result2 = extract_reference_no(sample_email_2, customer_id=2693)
    print(f"Reference Nos: {result2['reference_nos']}")
    print(f"Error: {result2['error']}")
    print("==============================\n")

    return result1, result2


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Run test
    test_subagent()

