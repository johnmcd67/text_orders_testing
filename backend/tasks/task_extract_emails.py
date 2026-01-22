"""
Task 2: Extract Original Emails from Forwarded Threads
Replaces manual Claude Code step - uses Anthropic API to extract original emails
Saves extracted data to temp/emails_extracted.json
"""
import os
import json
from typing import List, Dict, Any

from anthropic import Anthropic
from backend.celery_app import celery_app
from backend.database import (
    update_job_status,
    update_job_progress_with_message,
    fail_job
)
from backend.utils.logger import logger
from backend.utils.blob_storage import load_json, save_json


def create_extraction_prompt(email_body: str) -> str:
    """
    Create prompt for extracting original email from forwarded thread
    
    Args:
        email_body: Raw email body content
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""You are an expert at extracting original emails from forwarded email threads.

Your task is to extract the original order email from this forwarded email thread.

CRITICAL INSTRUCTIONS:

1. Find the original email in the forwarded thread:
   - Search for the LAST occurrence of "De:" in the email body (working from bottom to top)
   - This "De:" marker indicates the start of the original email
   - There will always be a "De:" marker, and there will only be one in the original email

2. Extract original email metadata from the "De:" block:
   - From address: Parse the "De:" line (e.g., "De: sender name <email@example.com>")
   - Subject: Parse the "Asunto:" line that follows the "De:" line
   - Date: Parse the "Fecha:" or "Enviado el:" line

3. Extract the original email body:
   - Everything AFTER the "De: / Enviado el: / Para: / Asunto:" header block is the original email content
   - This is the actual order content we need

4. Apply footer splitting to the original email body ONLY:
   - Use Spanish signature markers to split body from footer:
     - "Atentamente"
     - "CONFIDENCIALIDAD"
     - "Antes de imprimir"
     - "Saludos"
     - "Cordialmente"
     - "Este mensaje"
     - "Este correo"
     - "Aviso legal"
     - "Avís legal"
     - "PROTECCIÓN DE DATOS"
     - "De conformidad con lo dispuesto"
   - Find the FIRST occurrence of any marker
   - Split: everything before = body, everything from marker onwards = footer

5. Keep the full email thread:
   - Store the complete email body as full_thread_body
   - This includes ALL emails in the forwarding chain (important for context)

EMAIL BODY:
{email_body}

Return your response as JSON with this exact structure:
{{
  "original_email": {{
    "from": "email@example.com",
    "subject": "Order subject",
    "date": "Date string",
    "footer": "Footer content if found, empty string if not"
  }},
  "full_thread_body": "[Complete email thread including all forwards and original email]"
}}

IMPORTANT:
- The original_email.from should be the email address from the LAST "De:" line (the original sender)
- The original_email.subject should be from the "Asunto:" line of the original email
- The original_email.date should be from the "Fecha:" or "Enviado el:" line of the original email
- The original_email.footer should ONLY contain the footer/signature from the original email (after applying Spanish marker splitting)
- The full_thread_body should be the ENTIRE email thread (all forwarded emails + original email)
"""
    return prompt


@celery_app.task(bind=True)
def extract_emails_task(self, job_id: int):
    """
    Extract original emails from forwarded threads using Anthropic API
    
    Args:
        job_id: ID of the job in job_runs table
        
    Returns:
        dict: Status and count of emails extracted
    """
    try:
        # Update job status
        update_job_status(job_id, "running")
        update_job_progress_with_message(job_id, 0, "Starting email extraction...")

        # Initialize Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        client = Anthropic(api_key=api_key)
        model = os.getenv("ANTHROPIC_MODEL_DEFAULT", "claude-sonnet-4-5-20250929")

        # Load raw emails from storage (Azure Blob or local)
        raw_emails = load_json('emails_raw.json')

        logger.info(f"[Task 2] Processing {len(raw_emails)} emails for extraction")

        # Process each email
        extracted_emails = []

        for idx, email_data in enumerate(raw_emails, 1):
            # Update progress
            progress = int((idx / len(raw_emails)) * 90)  # 0% to 90%
            msg = f"Extracting email {idx}/{len(raw_emails)}..."
            update_job_progress_with_message(job_id, progress, msg)

            message_id = email_data.get('message_id', '')
            body_raw = email_data.get('body_raw', '')

            logger.info(f"[Task 2] Processing email {idx}/{len(raw_emails)}: {message_id[:50]}...")

            try:
                # Create extraction prompt
                prompt = create_extraction_prompt(body_raw)

                # Call Anthropic API
                response = client.messages.create(
                    model=model,
                    max_tokens=4096,
                    temperature=0,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )

                # Parse JSON response
                content = response.content[0].text

                # Try to extract JSON from response
                try:
                    extracted_data = json.loads(content)
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown code blocks
                    if "```json" in content:
                        json_str = content.split("```json")[1].split("```")[0].strip()
                        extracted_data = json.loads(json_str)
                    elif "```" in content:
                        json_str = content.split("```")[1].split("```")[0].strip()
                        extracted_data = json.loads(json_str)
                    else:
                        raise ValueError(f"Could not parse JSON from response: {content[:200]}")

                # Validate extracted data structure
                if 'original_email' not in extracted_data or 'full_thread_body' not in extracted_data:
                    raise ValueError("Missing required fields in extracted data")

                # Add message_id to extracted data
                extracted_data['message_id'] = message_id

                extracted_emails.append(extracted_data)
                logger.info(f"[Task 2] ✓ Email {idx} extracted successfully")

            except Exception as e:
                logger.error(f"[Task 2] ✗ Failed to extract email {idx}: {str(e)}")
                # Continue with other emails even if one fails
                # Add a placeholder entry to maintain count
                extracted_emails.append({
                    'message_id': message_id,
                    'original_email': {
                        'from': '',
                        'subject': email_data.get('subject', ''),
                        'date': email_data.get('date', ''),
                        'footer': ''
                    },
                    'full_thread_body': body_raw,
                    'extraction_error': str(e)
                })

        # Save extracted emails to storage (Azure Blob or local)
        update_job_progress_with_message(job_id, 95, "Saving extracted email data...")
        saved_path = save_json(extracted_emails, 'emails_extracted.json')

        logger.info(f"[Task 2] ✓ Task 2 Complete")
        logger.info(f"[Task 2]   Total emails extracted: {len(extracted_emails)}")
        logger.info(f"[Task 2]   Data saved to: {saved_path}")

        update_job_progress_with_message(job_id, 100, f"Email extraction complete. Processed {len(extracted_emails)} emails.")

        # Auto-chain to Task 3 (Extract Data)
        from backend.tasks.task_extract_data import extract_data_task
        extract_data_task.delay(job_id)

        return {
            "status": "completed",
            "emails_extracted": len(extracted_emails)
        }

    except Exception as e:
        # Fatal error - mark job as failed
        error_message = f"Task 2 (Email Extraction) failed: {str(e)}"
        logger.error(f"[Task 2] ✗ {error_message}")
        fail_job(job_id, error_message)
        raise

