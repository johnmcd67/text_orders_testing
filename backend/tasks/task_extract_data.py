"""
Task 3: Data Extraction
Converts extracted emails to CSV format and processes through subagents
Generates order_details.csv and pauses for user review
"""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import pandas as pd

from backend.celery_app import celery_app
from backend.database import (
    update_job_status,
    update_job_progress_with_message,
    fail_job
)
from backend.utils.blob_storage import load_json, save_csv, file_exists

# Import subagents
from backend.subagents.customer_id import extract_customer_id
from backend.subagents.sku_extraction import extract_sku_and_quantity
from backend.subagents.reference_no import extract_reference_no
from backend.subagents.valve_detection import detect_valve_request
from backend.subagents.delivery_address import extract_delivery_address
from backend.subagents.cpsd_extraction import extract_cpsd
from backend.subagents.options_extraction import extract_options
from backend.utils.database import get_db_helper


def format_email_content(original_email, full_thread_body, message_id):
    """
    Format email data into the standard output format for subagents
    Matches the format from finalize_text_orders.py
    
    Args:
        original_email: Dict with from, subject, date, footer
        full_thread_body: Complete email thread content
        message_id: Email message ID
        
    Returns:
        Formatted email text string
    """
    sections = []

    # EMAIL HEADER (from original email only)
    sections.append("--- EMAIL HEADER ---")
    sections.append(f"From: {original_email.get('from', '')}")
    sections.append(f"Subject: {original_email.get('subject', '')}")
    sections.append(f"Date: {original_email.get('date', '')}")
    sections.append("")

    # EMAIL BODY (full thread - all emails)
    sections.append("--- EMAIL BODY ---")
    sections.append(full_thread_body)
    sections.append("")

    # EMAIL FOOTER (from original email only)
    sections.append("--- EMAIL FOOTER ---")
    sections.append(original_email.get('footer', ''))
    sections.append("")

    # ENTRY ID
    sections.append("--- ENTRY ID ---")
    sections.append(message_id)

    return "\n".join(sections)


def process_single_email(
    email_text: str,
    order_number: int,
    message_id: str,
    job_id: int,
    total_emails: int,
    email_metadata_map: Dict[str, Dict[str, str]] = None
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Process a single email through all subagents

    Args:
        email_text: Formatted email content (with headers/footers)
        order_number: Sequential order number
        message_id: Email ID from Microsoft Graph (will become entry_id in DB)
        job_id: Job ID for progress tracking
        total_emails: Total number of emails (for progress calculation)

    Returns:
        Tuple of (order_lines, failure_contexts) where:
        - order_lines: List of order dictionaries (may be multiple if multi-line order)
        - failure_contexts: List of failure context dictionaries for summary generation
    """
    failure_contexts = []  # Collect failure contexts for this email
    print(f"[Task 3] " + "=" * 60)
    print(f"[Task 3] Processing Order {order_number}/{total_emails}")
    print(f"[Task 3] " + "=" * 60)

    # Update progress message
    update_job_progress_with_message(
        job_id,
        int((order_number / total_emails) * 80),  # 0-80% for processing emails
        f"Processing email {order_number}/{total_emails}... Extracting customer ID"
    )

    # Phase 1: Extract Customer ID (Sequential)
    print(f"[Task 3] Phase 1: Extracting customer ID...")

    # Prepend email metadata (subject, from) for customer extraction ONLY
    # This ensures the LLM can see the subject line which often contains the customer name
    email_text_with_metadata = email_text
    if email_metadata_map and message_id and message_id in email_metadata_map:
        metadata = email_metadata_map[message_id]
        email_header = f"EMAIL METADATA:\nSubject: {metadata['subject']}\nFrom: {metadata['from']}\nTo: {metadata['to']}\nDate: {metadata['date']}\n\nEMAIL CONTENT:\n"
        email_text_with_metadata = email_header + email_text
        print(f"[Task 3] Added email metadata for customer extraction - Subject: {metadata['subject'][:50]}...")

    customer_result = extract_customer_id(email_text_with_metadata)

    if customer_result.get("error") or not customer_result.get("customer_id"):
        print(f"[Task 3] Order {order_number}: Failed to extract customer ID - {customer_result.get('error')}")
        # Capture failure context if available
        if customer_result.get("failure_context"):
            fc = customer_result["failure_context"]
            fc["order_number"] = order_number
            fc["entry_id"] = message_id
            failure_contexts.append(fc)
        return ([{
            "orderno": order_number,
            "customerid": None,
            "customer_name": None,
            "sku": None,
            "quantity": None,
            "reference_no": None,
            "valve": "no",
            "delivery_address": None,
            "cpsd": None,
            "entry_id": message_id,
            "option_sku": None,
            "option_qty": None,
            "telephone_number": None,
            "contact_name": None,
            "error": customer_result.get("error", "Unknown error"),
            "email_text": email_text[:500]
        }], failure_contexts)

    customer_id = customer_result["customer_id"]
    customer_name = customer_result["customer_name"]
    print(f"[Task 3] Customer ID: {customer_id} ({customer_name})")

    # Phase 2: Extract SKU & Quantity (Sequential)
    update_job_progress_with_message(
        job_id,
        int((order_number / total_emails) * 80),
        f"Processing email {order_number}/{total_emails}... Extracting SKUs"
    )
    print(f"[Task 3] Phase 2: Extracting SKU & quantity...")
    sku_result = extract_sku_and_quantity(email_text)

    if sku_result.get("error") or not sku_result.get("order_lines"):
        print(f"[Task 3] Order {order_number}: Failed to extract SKU - {sku_result.get('error')}")
        # Capture failure context if available
        if sku_result.get("failure_context"):
            fc = sku_result["failure_context"]
            fc["order_number"] = order_number
            fc["entry_id"] = message_id
            fc["customer_id"] = customer_id
            fc["customer_name"] = customer_name
            failure_contexts.append(fc)
        return ([{
            "orderno": order_number,
            "customerid": customer_id,
            "customer_name": customer_name,
            "sku": None,
            "quantity": None,
            "reference_no": None,
            "valve": "no",
            "delivery_address": None,
            "cpsd": None,
            "entry_id": message_id,
            "option_sku": None,
            "option_qty": None,
            "telephone_number": None,
            "contact_name": None,
            "error": sku_result.get("error", "Unknown error"),
            "email_text": email_text[:500]
        }], failure_contexts)

    order_lines = sku_result["order_lines"]
    print(f"[Task 3] Extracted {len(order_lines)} order line(s)")

    # Phase 3: Extract additional fields (Parallel)
    update_job_progress_with_message(
        job_id,
        int((order_number / total_emails) * 80),
        f"Processing email {order_number}/{total_emails}... Running parallel subagents"
    )
    print(f"[Task 3] Phase 3: Extracting reference, valve, address, CPSD, options (parallel)...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(extract_reference_no, email_text, customer_id): "reference_no",
            executor.submit(detect_valve_request, email_text, len(order_lines)): "valve",
            executor.submit(extract_delivery_address, email_text, customer_id, customer_name): "delivery_address",
            executor.submit(extract_cpsd, email_text): "cpsd",
            executor.submit(extract_options, email_text, order_lines): "options",
        }

        results = {}
        for future in as_completed(futures):
            field_name = futures[future]
            try:
                result = future.result()
                results[field_name] = result
                # Log progress for each subagent
                if field_name == "cpsd":
                    print(f"[Task 3]   cpsds: {result.get('cpsds')}")
                    print(f"[Task 3]   entry_id: {result.get('entry_id')}")
                elif field_name == "reference_no":
                    print(f"[Task 3]   reference_nos: {result.get('reference_nos')}")
                elif field_name == "delivery_address":
                    print(f"[Task 3]   delivery_address: {result.get('delivery_address')}")
                    print(f"[Task 3]   telephone_number: {result.get('telephone_number')}")
                    print(f"[Task 3]   contact_name: {result.get('contact_name')}")
                elif field_name == "options":
                    print(f"[Task 3]   option_sku: {result.get('option_sku')}")
                    print(f"[Task 3]   option_qty: {result.get('option_qty')}")
                elif field_name == "valve":
                    print(f"[Task 3]   valves: {result.get('valves')}")
                else:
                    print(f"[Task 3]   {field_name}: {result.get(field_name)}")
            except Exception as e:
                print(f"[Task 3]   {field_name} extraction failed: {e}")
                results[field_name] = {field_name: None, "error": str(e)}

    # Phase 4: Merge all data
    print(f"[Task 3] Phase 4: Merging data...")
    merged_orders = []

    # Extract cpsds array and entry_id from cpsd subagent
    cpsds = results["cpsd"].get("cpsds", [])
    # Use entry_id from cpsd subagent if available, otherwise use message_id
    entry_id_from_cpsd = results["cpsd"].get("entry_id")
    final_entry_id = entry_id_from_cpsd if entry_id_from_cpsd else message_id

    # Extract reference_nos array
    reference_nos = results["reference_no"].get("reference_nos", [])

    # Handle CPSD assignment logic
    num_lines = len(order_lines)
    num_cpsds = len(cpsds) if cpsds else 0

    if num_cpsds == num_lines:
        print(f"[Task 3] Pairing {num_cpsds} CPSDs with {num_lines} order lines (1-to-1)")
        cpsd_assignments = cpsds
    elif num_cpsds == 1:
        print(f"[Task 3] Applying single CPSD to all {num_lines} order lines")
        cpsd_assignments = [cpsds[0]] * num_lines
    elif num_cpsds == 0:
        print(f"[Task 3] No CPSDs found, using None for all {num_lines} order lines")
        cpsd_assignments = [None] * num_lines
    else:
        print(f"[Task 3] CPSD count mismatch: {num_cpsds} CPSDs vs {num_lines} order lines - using None")
        cpsd_assignments = [None] * num_lines

    # Handle reference_no assignment logic
    num_refs = len(reference_nos) if reference_nos else 0

    if num_refs == num_lines:
        print(f"[Task 3] Pairing {num_refs} reference numbers with {num_lines} order lines (1-to-1)")
        ref_assignments = reference_nos
    elif num_refs == 1:
        print(f"[Task 3] Applying single reference number to all {num_lines} order lines")
        ref_assignments = [reference_nos[0]] * num_lines
    elif num_refs > 1 and num_lines == 1:
        print(f"[Task 3] Combining {num_refs} references for single order line")
        ref_assignments = [", ".join(reference_nos)]
    elif num_refs == 0:
        print(f"[Task 3] No reference numbers found, using None for all {num_lines} order lines")
        ref_assignments = [None] * num_lines
    else:
        print(f"[Task 3] Reference number count mismatch: {num_refs} references vs {num_lines} order lines - using None")
        ref_assignments = [None] * num_lines

    # Handle valve assignment logic (now returns array)
    valve_assignments = results["valve"].get("valves", ["no"] * num_lines)
    num_valves = len(valve_assignments) if valve_assignments else 0

    if num_valves == num_lines:
        print(f"[Task 3] Pairing {num_valves} valve assignments with {num_lines} order lines (1-to-1)")
    elif num_valves < num_lines:
        print(f"[Task 3] Valve array too short ({num_valves} vs {num_lines}), padding with 'no'")
        valve_assignments.extend(["no"] * (num_lines - num_valves))
    else:
        print(f"[Task 3] Valve array too long ({num_valves} vs {num_lines}), truncating")
        valve_assignments = valve_assignments[:num_lines]

    # Build merged orders with paired CPSDs and reference numbers
    for idx, line in enumerate(order_lines):
        merged_order = {
            "orderno": order_number,
            "customerid": customer_id,
            "customer_name": customer_name,
            "sku": line["sku"],
            "quantity": line["quantity"],
            "reference_no": ref_assignments[idx],
            "valve": valve_assignments[idx],
            "delivery_address": results["delivery_address"].get("delivery_address"),
            "cpsd": cpsd_assignments[idx],
            "entry_id": final_entry_id,
            "option_sku": results["options"].get("option_sku"),
            "option_qty": results["options"].get("option_qty"),
            "telephone_number": results["delivery_address"].get("telephone_number"),
            "contact_name": results["delivery_address"].get("contact_name"),
        }
        merged_orders.append(merged_order)

    print(f"[Task 3] Order {order_number}: Successfully processed {len(merged_orders)} line(s)")
    return (merged_orders, failure_contexts)


@celery_app.task(bind=True)
def extract_data_task(self, job_id: int):
    """
    Extract data from extracted emails using multi-agent orchestrator

    Args:
        job_id: ID of the job in job_runs table

    Returns:
        dict: Status and statistics
    """
    try:
        # Update job status to running
        update_job_status(job_id, "running")
        update_job_progress_with_message(job_id, 0, "Initializing data extraction...")

        print(f"[Task 3] " + "=" * 80)
        print(f"[Task 3] DATA EXTRACTION - STARTING")
        print(f"[Task 3] " + "=" * 80)

        # Step 1: Read extracted emails from storage (Azure Blob or local)
        print(f"[Task 3] Reading extracted emails from storage...")
        extracted_emails = load_json('emails_extracted.json')

        print(f"[Task 3] Found {len(extracted_emails)} email(s) to process")

        if not extracted_emails:
            print(f"[Task 3] No emails found in extracted data")
            return {
                "status": "completed",
                "orders_processed": 0,
                "message": "No emails to process"
            }

        # Load email metadata (subject, from, etc.) from emails_raw.json
        email_metadata_map = {}
        if file_exists("emails_raw.json"):
            emails_data = load_json("emails_raw.json")
            # Create mapping: message_id → email metadata
            for email in emails_data:
                msg_id = email.get("message_id")
                if msg_id:
                    email_metadata_map[msg_id] = {
                        "subject": email.get("subject", ""),
                        "from": email.get("from", ""),
                        "to": email.get("to", ""),
                        "date": email.get("date", "")
                    }
            print(f"[Task 3] Loaded email metadata for {len(email_metadata_map)} emails")
        else:
            print(f"[Task 3] Warning: emails_raw.json not found - subject lines won't be available")

        # Step 2: Process each email
        all_orders = []
        all_failure_contexts = []  # Collect failure contexts for summary generation
        order_number = 1

        for idx, email_data in enumerate(extracted_emails, 1):
            print(f"[Task 3] \nProcessing email {idx}/{len(extracted_emails)}...")

            # Extract email components
            message_id = email_data.get('message_id', '')
            original_email = email_data.get('original_email', {})
            full_thread_body = email_data.get('full_thread_body', '')

            if not message_id:
                print(f"[Task 3] Warning: No message_id in extracted email {idx}")
                message_id = f"missing_{idx}"

            # Format email content for subagents (matches finalize_text_orders.py format)
            email_text = format_email_content(original_email, full_thread_body, message_id)

            try:
                # Process email (may return multiple order lines and failure contexts)
                order_lines, failure_contexts = process_single_email(
                    email_text,
                    order_number,
                    message_id,
                    job_id,
                    len(extracted_emails),
                    email_metadata_map
                )
                all_orders.extend(order_lines)
                all_failure_contexts.extend(failure_contexts)

                # Increment order number for next email
                order_number += 1

            except Exception as e:
                print(f"[Task 3] Failed to process email {idx}: {e}", exc_info=True)
                # Add failed order placeholder
                all_orders.append({
                    "orderno": order_number,
                    "customerid": None,
                    "customer_name": None,
                    "sku": None,
                    "quantity": None,
                    "reference_no": None,
                    "valve": "no",
                    "delivery_address": None,
                    "cpsd": None,
                    "entry_id": message_id,
                    "option_sku": None,
                    "option_qty": None,
                    "telephone_number": None,
                    "contact_name": None,
                    "error": str(e),
                    "email_text": email_text[:500]
                })
                # Add exception failure context
                all_failure_contexts.append({
                    "type": "exception",
                    "order_number": order_number,
                    "entry_id": message_id,
                    "exception_message": str(e),
                    "email_snippet": email_text[:500] if email_text else None
                })
                order_number += 1

        print(f"[Task 3] \nProcessed {len(extracted_emails)} email(s), generated {len(all_orders)} order line(s)")

        # Step 3: Write order_details.csv to storage (Azure Blob or local)
        update_job_progress_with_message(job_id, 85, "Generating order_details.csv...")
        print(f"[Task 3] Writing order_details.csv to storage...")

        try:
            df_output = pd.DataFrame(all_orders)

            # Select columns for output (exclude error and email_text)
            output_columns = [
                "orderno", "customerid", "customer_name", "sku", "quantity",
                "reference_no", "valve", "delivery_address", "cpsd", "entry_id",
                "option_sku", "option_qty", "telephone_number", "contact_name"
            ]
            df_output = df_output[output_columns]

            saved_path = save_csv(df_output, 'order_details.csv')
            print(f"[Task 3] Successfully wrote {len(df_output)} row(s) to {saved_path}")
        except Exception as e:
            print(f"[Task 3] Failed to write order_details.csv: {e}")
            raise

        # Step 4: Save failure contexts to database for summary generation
        if all_failure_contexts:
            print(f"[Task 3] Saving {len(all_failure_contexts)} failure context(s) to database...")
            try:
                db_helper = get_db_helper()
                db_helper.save_failure_context(job_id, all_failure_contexts)
                print(f"[Task 3] Successfully saved failure contexts")
            except Exception as e:
                print(f"[Task 3] Warning: Failed to save failure contexts: {e}")
                # Don't raise - this is not critical for job completion

        # Summary
        update_job_progress_with_message(job_id, 90, "Data extraction complete. Ready for review.")
        print(f"[Task 3] \n" + "=" * 80)
        print(f"[Task 3] DATA EXTRACTION - COMPLETE")
        print(f"[Task 3] " + "=" * 80)
        print(f"[Task 3] Total emails processed: {len(extracted_emails)}")
        print(f"[Task 3] Total order lines generated: {len(all_orders)}")
        print(f"[Task 3] Output files:")
        print(f"[Task 3]   - order_details.csv: {saved_path}")
        print(f"[Task 3] Note: Database insertion will occur after user approval (Task 4)")
        print(f"[Task 3] " + "=" * 80)

        # Update job status to awaiting_review_data (Pause Point)
        update_job_status(job_id, "awaiting_review_data")
        update_job_progress_with_message(
            job_id,
            100,
            f"Data extraction complete. {len(all_orders)} orders ready for review."
        )

        return {
            "status": "awaiting_review",
            "emails_processed": len(extracted_emails),
            "orders_generated": len(all_orders)
        }

    except Exception as e:
        # Fatal error - mark job as failed
        error_message = f"Task 3 (Data Extraction) failed: {str(e)}"
        print(f"[Task 3] ✗ {error_message}")
        import traceback
        traceback.print_exc()
        fail_job(job_id, error_message)
        raise

