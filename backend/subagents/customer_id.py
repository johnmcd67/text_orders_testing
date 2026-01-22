"""
Subagent 1: Customer ID Extraction
Extracts customer name from email and matches against database using fuzzy matching
"""
import re
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from backend.utils.anthropic_helper import get_anthropic_helper
from backend.utils.database import get_db_helper
from backend.utils.logger import logger


def load_prompt_template() -> str:
    """Load the customer ID prompt template"""
    prompt_file = Path(__file__).parent.parent / "prompts" / "customer_id.txt"
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read()


def extract_sender_email_from_text(email_text: str) -> Optional[str]:
    """
    Extract the original sender's email address from email text.

    Logic:
    1. Start from the BOTTOM of the email text
    2. Find the FIRST occurrence of "De:" (Spanish, case-insensitive)
    3. Extract the email address that follows

    Email formats supported:
    - "De: Name <email@example.com>" -> extract email@example.com
    - "De: email@example.com" -> extract email@example.com
    - "**De:** Name <email@example.com>" -> extract email@example.com (bold markdown)
    - "De: Name <email@example.com> Enviado el: ..." -> inline format

    Args:
        email_text: Full email thread text

    Returns:
        Email address string (lowercase) or None if not found
    """
    if not email_text:
        return None

    # Split text into lines and reverse to process from bottom to top
    lines = email_text.split('\n')
    lines.reverse()

    # Pattern to match "De:" at start of line (case-insensitive), allowing optional markdown bold
    de_at_start_pattern = re.compile(r'^\s*\*{0,2}de:\*{0,2}\s*', re.IGNORECASE)

    # Pattern to match "De:" anywhere in the line (for inline formats like header blocks)
    # Matches: "De: Name <email>" or "**De:** Name <email>" anywhere in line
    de_anywhere_pattern = re.compile(r'\bde:\s*', re.IGNORECASE)

    # Pattern to extract email from angle brackets: <email@example.com>
    email_in_brackets = re.compile(r'<([^>]+@[^>]+)>')

    # Pattern to extract standalone email: email@example.com
    standalone_email = re.compile(r'[\w.+-]+@[\w.-]+\.\w+')

    # First pass: Look for "De:" at start of line (preferred - more specific)
    for line in lines:
        if de_at_start_pattern.match(line):
            # Found "De:" at start of line - extract email
            bracket_match = email_in_brackets.search(line)
            if bracket_match:
                email = bracket_match.group(1).strip().lower()
                logger.info(f"Extracted sender email from brackets: {email}")
                return email

            email_match = standalone_email.search(line)
            if email_match:
                email = email_match.group(0).strip().lower()
                logger.info(f"Extracted sender email (standalone): {email}")
                return email

            logger.warning(f"Found 'De:' at start but could not extract email: {line[:100]}")
            return None

    # Second pass: Look for "De:" anywhere in line (handles inline header formats)
    # This catches formats like: "De: Daniel Montesinos Vicent <brosmovi@hotmail.com> Enviado el: ..."
    for line in lines:
        de_match = de_anywhere_pattern.search(line)
        if de_match:
            # Extract the portion of the line after "De:"
            after_de = line[de_match.end():]

            # First try: email in angle brackets after "De:"
            bracket_match = email_in_brackets.search(after_de)
            if bracket_match:
                email = bracket_match.group(1).strip().lower()
                logger.info(f"Extracted sender email from inline 'De:' (brackets): {email}")
                return email

            # Second try: standalone email after "De:"
            email_match = standalone_email.search(after_de)
            if email_match:
                email = email_match.group(0).strip().lower()
                logger.info(f"Extracted sender email from inline 'De:' (standalone): {email}")
                return email

            # "De:" found but no email extracted - continue searching other lines
            logger.debug(f"Found inline 'De:' but no email in: {line[:100]}")

    logger.warning("No 'De:' line found in email text")
    return None


def try_email_lookup_fallback(email_text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to identify customer via email lookup fallback.

    This is called when:
    - LLM returns zero customer names, OR
    - Fuzzy match fails to find a match above threshold

    Process:
    1. Extract sender email from email text (bottom-up "De:" search)
    2. Look up email in public.email_lookup_for_customer table
    3. Return customer info if found, None otherwise

    Args:
        email_text: Full email thread text

    Returns:
        Dictionary with customer_id, customer_name if found, None otherwise
    """
    logger.info("Attempting email lookup fallback...")

    # Step 1: Extract sender email
    sender_email = extract_sender_email_from_text(email_text)

    if not sender_email:
        logger.warning("Email lookup fallback: Could not extract sender email")
        return None

    # Step 2: Look up in database
    db_helper = get_db_helper()
    result = db_helper.lookup_customer_by_email(sender_email)

    if result:
        customer_id, customer_name = result
        logger.info(f"Email lookup fallback SUCCESS: {sender_email} -> ID={customer_id}, Name={customer_name}")
        return {
            "customer_id": customer_id,
            "customer_name": customer_name,
            "matched_via": "email_lookup",
            "matched_email": sender_email
        }

    logger.info(f"Email lookup fallback: No match for {sender_email}")
    return None


def extract_customer_id(email_text: str) -> Dict[str, Optional[any]]:
    """
    Extract customer ID from email text

    Process:
    1. Use gpt-4o to extract customer information from email
    2. If LLM provides customer_id directly (hardcoded customers like NEWKER, FERROLAN→ALANTA), use it
    3. Otherwise, fuzzy match against public.clients database table
    4. Return customer ID and customer name

    Args:
        email_text: Raw email content (cleaned)

    Returns:
        Dictionary with:
        - customer_id (int or None): Matched customer ID
        - customer_name (str or None): Matched customer name from database
        - potential_names (list): Names extracted by LLM (for debugging)
        - error (str or None): Error message if extraction failed
    """
    logger.info("Subagent 1: Starting customer ID extraction")

    try:
        # Step 1: Load prompt template
        prompt_template = load_prompt_template()
        prompt = prompt_template.format(email_text=email_text)

        # Step 2: Call Claude to extract customer information
        anthropic_helper = get_anthropic_helper()
        response = anthropic_helper.call_complex(prompt=prompt)

        # Step 3: Check if LLM provided customer_id directly (hardcoded customers)
        customer_id_from_llm = response.get("customer_id")
        customer_name_from_llm = response.get("customer_name")
        needs_fuzzy_match = response.get("needs_fuzzy_match", True)

        # If LLM provided customer_id directly, use it (NEWKER, FERROLAN→ALANTA)
        if customer_id_from_llm is not None and not needs_fuzzy_match:
            logger.info(f"LLM provided hardcoded customer: ID={customer_id_from_llm}, Name={customer_name_from_llm}")
            return {
                "customer_id": customer_id_from_llm,
                "customer_name": customer_name_from_llm,
                "potential_names": [customer_name_from_llm],
                "error": None
            }

        # Step 4: Fall back to fuzzy matching for other customers
        potential_names = response.get("customer_names", [])
        logger.info(f"LLM extracted potential customer names: {potential_names}")

        if not potential_names:
            logger.warning("No customer names found in email, trying email lookup fallback...")

            # FALLBACK: Try email lookup
            fallback_result = try_email_lookup_fallback(email_text)
            if fallback_result:
                return {
                    "customer_id": fallback_result["customer_id"],
                    "customer_name": fallback_result["customer_name"],
                    "potential_names": [],
                    "matched_via": fallback_result.get("matched_via"),
                    "matched_email": fallback_result.get("matched_email"),
                    "error": None
                }

            # Fallback also failed
            return {
                "customer_id": None,
                "customer_name": None,
                "potential_names": [],
                "error": "No customer names found in email and email lookup fallback failed"
            }

        # Step 5: Fuzzy match against database with stricter threshold
        db_helper = get_db_helper()
        threshold = 0.85  # 85% similarity required (raised from 0.6)
        customer_id, customer_name, match_details = db_helper.fuzzy_match_customer(
            potential_names=potential_names,
            threshold=threshold
        )

        if customer_id is None:
            logger.warning(f"No database match found for: {potential_names}, trying email lookup fallback...")

            # FALLBACK: Try email lookup before giving up
            fallback_result = try_email_lookup_fallback(email_text)
            if fallback_result:
                return {
                    "customer_id": fallback_result["customer_id"],
                    "customer_name": fallback_result["customer_name"],
                    "potential_names": potential_names,
                    "matched_via": fallback_result.get("matched_via"),
                    "matched_email": fallback_result.get("matched_email"),
                    "error": None
                }

            # Fallback also failed - return original error with enhanced context
            logger.warning(f"Email lookup fallback also failed for: {potential_names}")
            failure_context = {
                "type": "customer_id",
                "extracted_names": potential_names,
                "best_match_name": match_details.get("best_match_name"),
                "best_match_id": match_details.get("best_match_id"),
                "best_match_score": match_details.get("best_score"),
                "threshold_used": threshold,
                "email_snippet": email_text[:500] if email_text else None,
                "email_lookup_attempted": True,
                "email_lookup_address": extract_sender_email_from_text(email_text)
            }
            return {
                "customer_id": None,
                "customer_name": None,
                "potential_names": potential_names,
                "error": f"No database match found for: {potential_names} (email lookup also failed)",
                "failure_context": failure_context
            }

        # Success!
        logger.info(f"Customer ID extraction successful: ID={customer_id}, Name={customer_name}")
        return {
            "customer_id": customer_id,
            "customer_name": customer_name,
            "potential_names": potential_names,
            "error": None
        }

    except Exception as e:
        logger.error(f"Subagent 1 failed: {e}", exc_info=True)
        return {
            "customer_id": None,
            "customer_name": None,
            "potential_names": [],
            "error": str(e)
        }


# Convenience function for testing
def test_subagent():
    """Test the subagent with sample email"""
    sample_email = """
    ATTENTION: This email is from an external source - be careful of attachments and links.
    PEDIDO
    Gracias, Un saludo.

    De: Fidel Castro <>
    Enviado el: lunes, 29 de septiembre de 2025 12:52
    Para: Info ohmyshower <>
    Asunto: DISTRIBUCIONES GENERALIFE MARACENA, S.L. pedido

    De: generalife maracena <dist.generalife@gmail.com>
    Enviado: lunes, 29 de septiembre de 2025 12:49
    Para: Fidel Castro <>
    Asunto: pedido

    Te indico pedido:
    1 plato ducha nature 140x80 BLANCO
    1 plato ducha nature 150x80 BLANCO
    1 plato ducha nature 130x80 BLANCO

    saludos
    Cno de la Torrecilla, s/n
    18200 Maracena (Granada)
    (+34) 958 411 239
    email: dist.generalife@gmail.com
    """

    result = extract_customer_id(sample_email)
    print("\n=== Subagent 1 Test Result ===")
    print(f"Customer ID: {result['customer_id']}")
    print(f"Customer Name: {result['customer_name']}")
    print(f"Potential Names: {result['potential_names']}")
    print(f"Error: {result['error']}")
    print("==============================\n")

    return result


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Run test
    test_subagent()

