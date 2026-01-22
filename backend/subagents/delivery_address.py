"""
Subagent 5: Delivery Address Extraction
Extracts alternative delivery address from email and formats it properly
Uses LLM-first approach with database fallback (only if exactly 1 address)
Uses Claude Sonnet 4.5 (complex task)
"""
from pathlib import Path
from typing import Dict, Optional
from backend.utils.anthropic_helper import get_anthropic_helper
from backend.utils.database import get_db_helper
from backend.utils.logger import logger


def load_prompt_template() -> str:
    """Load the delivery address prompt template"""
    prompt_file = Path(__file__).parent.parent / "prompts" / "delivery_address.txt"
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()


def format_address_from_db(address: Dict[str, str]) -> str:
    """
    Format address from database fields into CSV format

    Args:
        address: Dict with street_address, post_code, city, province

    Returns:
        Formatted address string: "street, postcode, city, province"
    """
    parts = [
        address["street_address"],
        address["post_code"],
        address["city"],
        address["province"]
    ]
    return ", ".join(str(p) for p in parts if p)


def extract_delivery_address(
    email_text: str,
    customerid: Optional[int] = None,
    customer_name: str = None
) -> Dict[str, Optional[str]]:
    """
    Extract delivery address from email text using LLM-first approach

    Workflow:
    1. LLM extraction: Try to find address in email/PDF using Claude
    2. If LLM finds address: return it immediately
    3. If LLM returns null: fall back to database lookup
       3a. Query v_md_clients_addresses for customerid
       3b. If exactly 1 address found: use it
       3c. If 0 or >1 addresses found: return None

    Args:
        email_text: Raw email content (cleaned)
        customerid: Customer ID for database lookup (optional)
        customer_name: Customer name to help LLM identify correct address (optional)

    Returns:
        Dictionary with:
        - delivery_address (str or None): Formatted address or None
        - telephone_number (str or None): Telephone number extracted from delivery section (all customers)
        - contact_name (str or None): Contact name extracted from delivery section (all customers)
        - error (str or None): Error message if extraction failed
    """
    logger.info("Subagent 5: Starting delivery address extraction")
    if customerid:
        logger.info(f"Customer ID: {customerid}")
    if customer_name:
        logger.info(f"Customer name: {customer_name}")

    try:
        # STEP 1: LLM extraction (Primary)
        logger.info("Starting LLM-based address extraction")
        prompt_template = load_prompt_template()
        prompt = prompt_template.format(
            email_text=email_text,
            customerid=customerid if customerid else "NOT PROVIDED",
            customer_name=customer_name if customer_name else "NOT PROVIDED"
        )

        anthropic_helper = get_anthropic_helper()
        response = anthropic_helper.call_complex(prompt=prompt)

        delivery_address = response.get("delivery_address")
        telephone_number = response.get("telephone_number")
        contact_name = response.get("contact_name")

        if delivery_address:
            logger.info(f"LLM extracted address: {delivery_address}")
            if telephone_number:
                logger.info(f"LLM extracted telephone: {telephone_number}")
            if contact_name:
                logger.info(f"LLM extracted contact name: {contact_name}")
            return {
                "delivery_address": delivery_address,
                "telephone_number": telephone_number,
                "contact_name": contact_name,
                "error": None
            }
        else:
            logger.info("No delivery address found by LLM, attempting database fallback")

        # STEP 2: Database fallback (only if LLM returns null)
        if customerid:
            try:
                logger.info("Querying database for known addresses")
                db_helper = get_db_helper()
                known_addresses = db_helper.get_customer_addresses(customerid)

                if len(known_addresses) == 1:
                    # Exactly 1 address - use it
                    formatted_address = format_address_from_db(known_addresses[0])
                    logger.info(f"Using single database address: {formatted_address}")
                    return {
                        "delivery_address": formatted_address,
                        "telephone_number": None,
                        "contact_name": None,
                        "error": None
                    }
                elif len(known_addresses) > 1:
                    # Multiple addresses - return null
                    logger.info(f"Found {len(known_addresses)} addresses for customer {customerid}, returning null")
                    return {
                        "delivery_address": None,
                        "telephone_number": None,
                        "contact_name": None,
                        "error": None
                    }
                else:
                    # No addresses found
                    logger.info(f"No known addresses found for customer {customerid}")
                    return {
                        "delivery_address": None,
                        "telephone_number": None,
                        "contact_name": None,
                        "error": None
                    }
            except Exception as db_error:
                logger.error(f"Database query failed during fallback: {db_error}", exc_info=True)
                return {
                    "delivery_address": None,
                    "telephone_number": None,
                    "contact_name": None,
                    "error": f"Database fallback failed: {str(db_error)}"
                }
        else:
            logger.info("No customerid provided, cannot attempt database fallback")
            return {
                "delivery_address": None,
                "telephone_number": None,
                "contact_name": None,
                "error": None
            }

    except Exception as e:
        # LLM extraction failure - this is a critical error
        logger.error(f"Subagent 5 LLM extraction failed: {e}", exc_info=True)
        return {
            "delivery_address": None,
            "telephone_number": None,
            "contact_name": None,
            "error": f"LLM extraction failed: {str(e)}"
        }


# Convenience function for testing
def test_subagent():
    """Test the subagent with sample emails"""

    # Test 1: No delivery address
    sample_email_1 = """
    Te indico pedido:
    1 plato ducha nature 140x80 BLANCO
    saludos
    """

    # Test 2: Delivery address with Spanish accents
    sample_email_2 = """
    Te indico pedido:
    1 plato ducha nature 140x80 BLANCO

    Dirección de entrega:
    Cno de la Torrecilla, s/n
    18200 Maracena (Granada)
    """

    print("\n=== Subagent 5 Test 1 (No address) ===")
    result1 = extract_delivery_address(sample_email_1)
    print(f"Delivery Address: {result1['delivery_address']}")
    print(f"Error: {result1['error']}")

    print("\n=== Subagent 5 Test 2 (With address) ===")
    result2 = extract_delivery_address(sample_email_2)
    print(f"Delivery Address: {result2['delivery_address']}")
    print(f"Error: {result2['error']}")
    print("==============================\n")

    return result1, result2


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Run test
    test_subagent()

