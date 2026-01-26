"""
Subagent 7: Database Export
Validates order data and exports to PostgreSQL database
Writes failed orders to failed_orders.csv
"""
import os
from typing import List, Dict, Any
import pandas as pd
from backend.utils.database import get_db_helper
from backend.utils.logger import logger


def validate_order(order: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validate order data before insertion

    Args:
        order: Order dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Required fields
    required_fields = ["orderno", "customerid", "sku", "quantity"]

    for field in required_fields:
        if field not in order or order[field] is None:
            return False, f"Missing required field: {field}"

    # Validate SKU length (must be 13 characters)
    sku = order.get("sku", "")
    if len(sku) != 13:
        return False, f"Invalid SKU length: {sku} (expected 13 chars, got {len(sku)})"

    # Validate quantity (must be positive integer)
    try:
        qty = int(order.get("quantity", 0))
        if qty <= 0:
            return False, f"Invalid quantity: {qty} (must be > 0)"
    except (ValueError, TypeError):
        return False, f"Invalid quantity type: {order.get('quantity')}"

    # Validate valve field
    valve = order.get("valve", "no")
    valid_valve_values = {"Yes", "no", "Horizontal valve", "Vertical valve", "Rectangular valve"}
    if valve not in valid_valve_values:
        return False, f"Invalid valve value: {valve} (must be one of: {', '.join(sorted(valid_valve_values))})"

    return True, ""


def export_to_database(orders: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Export orders to PostgreSQL database

    Args:
        orders: List of order dictionaries with keys:
            - orderno (int)
            - customerid (int)
            - customer_name (str) - Customer name (can be overwritten at review stage)
            - sku (str) - 13 characters
            - quantity (int)
            - reference_no (str or None)
            - valve (str) - "Yes" or "no"
            - delivery_address (str or None)
            - cpsd (str or None) - YYYY-MM-DD format
            - entry_id (str or None) - EntryID from email
            - option_sku (str or None) - Option SKU for grids/covers
            - option_qty (int or None) - Option quantity
            - telephone_number (str or None) - Telephone number (only for customer_id 2156)
            - contact_name (str or None) - Contact name (only for NEWKER customers 4891-4895)

    Returns:
        Dictionary with:
        - success_count (int): Number of successful insertions
        - failed_count (int): Number of failed insertions
        - failed_orders (list): List of failed order dictionaries with error info
        - error (str or None): General error message if export failed
    """
    logger.info(f"Subagent 7: Starting database export for {len(orders)} orders")

    success_count = 0
    failed_count = 0
    failed_orders = []
    valid_orders = []

    try:
        db_helper = get_db_helper()

        # Step 1: Validate all orders
        for order in orders:
            is_valid, error_msg = validate_order(order)

            if not is_valid:
                logger.error(f"Validation failed for order {order.get('orderno')}: {error_msg}")
                failed_count += 1
                failed_orders.append({
                    **order,
                    "error_type": "Validation Error",
                    "error_message": error_msg
                })
                continue

            # Prepare data for insertion (map to database columns)
            order_data = {
                "orderno": order.get("orderno"),
                "customerid": order.get("customerid"),
                "customer_name": order.get("customer_name"),
                "13DigitAlias": order.get("sku"),  # Database column name
                "orderqty": order.get("quantity"),
                "reference_no": order.get("reference_no"),
                "valve": order.get("valve"),
                "delivery_address": order.get("delivery_address"),
                "alternative_cpsd": order.get("cpsd"),
                "entry_id": order.get("entry_id"),
                "option_sku": order.get("option_sku"),
                "option_qty": order.get("option_qty"),
                "telephone_number": order.get("telephone_number"),
                "contact_name": order.get("contact_name"),
                "job_id": order.get("job_id"),
            }

            valid_orders.append((order, order_data))

        # Step 2: Batch insert all valid orders in single transaction
        if valid_orders:
            logger.info(f"Inserting {len(valid_orders)} valid orders in batch...")

            orders_data = [order_data for _, order_data in valid_orders]
            success = db_helper.insert_orders_batch(orders_data)

            if success:
                success_count = len(valid_orders)
                logger.info(f"Successfully inserted {success_count} orders in batch")
                
                # Update job_runs with order and order line counts
                if orders_data:
                    job_id = orders_data[0].get("job_id")
                    if job_id:
                        try:
                            update_success = db_helper.update_job_runs_counts(job_id)
                            if update_success:
                                logger.info(f"Updated job_runs counts for job_id {job_id}")
                            else:
                                logger.warning(f"Failed to update job_runs counts for job_id {job_id}")
                        except Exception as e:
                            logger.error(f"Error updating job_runs counts for job_id {job_id}: {e}")
            else:
                # If batch fails, mark all as failed
                failed_count = len(valid_orders)
                for order, _ in valid_orders:
                    failed_orders.append({
                        **order,
                        "error_type": "Database Insert Error",
                        "error_message": "Batch insert failed"
                    })
                logger.error(f"Batch insert failed for {failed_count} orders")

        # Summary
        logger.info(f"Database export complete: {success_count} success, {failed_count} failed")

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_orders": failed_orders,
            "error": None
        }

    except Exception as e:
        logger.error(f"Subagent 7 failed: {e}", exc_info=True)
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_orders": failed_orders,
            "error": str(e)
        }


def write_failed_orders_csv(failed_orders: List[Dict[str, Any]], output_path: str) -> None:
    """
    Write failed orders to CSV file

    Args:
        failed_orders: List of failed order dictionaries with error info
        output_path: Path to failed_orders.csv
    """
    if not failed_orders:
        logger.info("No failed orders to write")
        return

    try:
        # Convert to DataFrame
        df = pd.DataFrame(failed_orders)

        # Reorder columns for readability
        column_order = [
            "orderno", "customerid", "customer_name", "sku", "quantity",
            "reference_no", "valve", "delivery_address", "cpsd", "entry_id",
            "option_sku", "option_qty", "telephone_number", "contact_name",
            "error_type", "error_message"
        ]

        # Only include columns that exist
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]

        # Write to CSV
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"Wrote {len(failed_orders)} failed orders to {output_path}")

    except Exception as e:
        logger.error(f"Failed to write failed_orders.csv: {e}", exc_info=True)


# Convenience function for testing
def test_subagent():
    """Test the subagent with sample orders"""
    sample_orders = [
        {
            "orderno": 1,
            "customerid": 2726,
            "customer_name": "DIST. GENERALIFE MARACENA S.L.",
            "sku": "NAT1400809003",
            "quantity": 1,
            "reference_no": None,
            "valve": "no",
            "delivery_address": "Cno de la Torrecilla s/n, 18200, Maracena, Granada",
            "cpsd": None,
            "entry_id": "AAMkADM5ODE3ZmlwLWM5YmEtNDBkZS05MzQ1LWY5ZmE1YjFkNl"
        },
        {
            "orderno": 1,
            "customerid": 2726,
            "customer_name": "DIST. GENERALIFE MARACENA S.L.",
            "sku": "NAT1500809003",
            "quantity": 1,
            "reference_no": None,
            "valve": "no",
            "delivery_address": "Cno de la Torrecilla s/n, 18200, Maracena, Granada",
            "cpsd": None,
            "entry_id": "AAMkADM5ODE3ZmlwLWM5YmEtNDBkZS05MzQ1LWY5ZmE1YjFkNl"
        },
        {
            "orderno": 2,
            "customerid": 9999,  # Invalid customer ID (for testing failure)
            "customer_name": "INVALID CUSTOMER",
            "sku": "INVALID",  # Invalid SKU (for testing validation)
            "quantity": 0,  # Invalid quantity
            "reference_no": None,
            "valve": "maybe",  # Invalid valve value
            "delivery_address": None,
            "cpsd": None,
            "entry_id": None
        }
    ]

    print("\n=== Subagent 7 Test ===")
    result = export_to_database(sample_orders)
    print(f"Success Count: {result['success_count']}")
    print(f"Failed Count: {result['failed_count']}")
    print(f"Error: {result['error']}")

    if result['failed_orders']:
        print(f"\nFailed Orders: {len(result['failed_orders'])}")
        for order in result['failed_orders']:
            print(f"  Order {order.get('orderno')}: {order.get('error_message')}")

    # Write failed orders CSV
    failed_csv_path = os.getenv("FAILED_ORDERS_CSV_PATH")
    if failed_csv_path and result['failed_orders']:
        write_failed_orders_csv(result['failed_orders'], failed_csv_path)
        print(f"\nFailed orders written to: {failed_csv_path}")

    print("==============================\n")

    return result


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Run test
    test_subagent()

