"""
Subagent 6: CPSD (Customer Promised Ship Date) Extraction
Extracts requested delivery date from email
"""
from pathlib import Path
from typing import Dict, Optional, List
from backend.utils.anthropic_helper import get_anthropic_helper
from backend.utils.logger import logger


def load_prompt_template() -> str:
    """Load the CPSD extraction prompt template"""
    prompt_file = Path(__file__).parent.parent / "prompts" / "cpsd_extraction.txt"
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()


def extract_cpsd(email_text: str) -> Dict[str, Optional[List[str]]]:
    """
    Extract CPSD (requested delivery dates) and EntryID from email text

    NOTE: Returns MULTIPLE CPSDs (one per product line) for tabular data,
    or a SINGLE CPSD (in an array) for natural language requests.

    Args:
        email_text: Raw email content (cleaned)

    Returns:
        Dictionary with:
        - cpsds (list or None): Array of dates in YYYY-MM-DD format, one per product line
        - entry_id (str or None): EntryID string or None
        - error (str or None): Error message if extraction failed
    """
    logger.info("Subagent 6: Starting CPSD and EntryID extraction")

    try:
        # Load prompt template
        prompt_template = load_prompt_template()
        prompt = prompt_template.format(email_text=email_text)

        # Call Claude to extract dates and EntryID
        anthropic_helper = get_anthropic_helper()
        response = anthropic_helper.call_default(prompt=prompt)

        # Extract cpsds array (new format)
        cpsds = response.get("cpsds", [])
        entry_id = response.get("entry_id")

        if cpsds and len(cpsds) > 0:
            logger.info(f"CPSD extracted: {len(cpsds)} date(s) - {cpsds}")
        else:
            logger.info("No CPSD found in email")

        if entry_id:
            logger.info(f"EntryID extracted: {entry_id}")
        else:
            logger.info("No EntryID found in email")

        return {
            "cpsds": cpsds if cpsds else [],
            "entry_id": entry_id,
            "error": None
        }

    except Exception as e:
        logger.error(f"Subagent 6 failed: {e}", exc_info=True)
        return {
            "cpsds": [],
            "entry_id": None,
            "error": str(e)
        }


# Convenience function for testing
def test_subagent():
    """Test the subagent with sample emails"""

    # Test 1: No delivery date
    sample_email_1 = """
    Te indico pedido:
    1 plato ducha nature 140x80 BLANCO
    saludos
    """

    # Test 2: With delivery date
    sample_email_2 = """
    Te indico pedido:
    1 plato ducha nature 140x80 BLANCO

    Fecha de entrega solicitada: 15 de octubre de 2025
    """

    # Test 3: Different date format
    sample_email_3 = """
    Te indico pedido:
    1 plato ducha nature 140x80 BLANCO

    Para el día 20/10/2025
    """

    print("\n=== Subagent 6 Test 1 (No date) ===")
    result1 = extract_cpsd(sample_email_1)
    print(f"CPSDs: {result1['cpsds']}")
    print(f"EntryID: {result1['entry_id']}")
    print(f"Error: {result1['error']}")

    print("\n=== Subagent 6 Test 2 (Spanish format) ===")
    result2 = extract_cpsd(sample_email_2)
    print(f"CPSDs: {result2['cpsds']}")
    print(f"EntryID: {result2['entry_id']}")
    print(f"Error: {result2['error']}")

    print("\n=== Subagent 6 Test 3 (Numeric format) ===")
    result3 = extract_cpsd(sample_email_3)
    print(f"CPSDs: {result3['cpsds']}")
    print(f"EntryID: {result3['entry_id']}")
    print(f"Error: {result3['error']}")
    print("==============================\n")

    return result1, result2, result3


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Run test
    test_subagent()

