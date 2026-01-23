"""
PostgreSQL database utilities
"""
import os
from typing import List, Tuple, Optional, Dict, Any
import json
from rapidfuzz import fuzz
import psycopg
from .logger import logger
from .text_normalizer import (
    remove_accents,
    normalize_business_name,
    extract_buying_group_keywords,
    calculate_boosted_similarity,
    calculate_jaro_winkler_similarity
)


class DatabaseHelper:
    """Helper for PostgreSQL database operations"""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database helper

        Args:
            database_url: PostgreSQL connection string (if None, reads from environment)
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in environment")

        self.connection = None

        # Cache for normalized customer data (populated on first fuzzy_match_customer call)
        # Structure: {
        #     customer_id: {
        #         "original": str,          # Original DB name (e.g., "BARROSO MORALES MARIA ANTONIA")
        #         "normalized": str,        # Normalized name (e.g., "antonio barroso maria morales")
        #         "keywords": list,         # Buying group keywords (e.g., ["gamma"])
        #         "is_personal": bool,      # True if personal name, False if business name
        #     }
        # }
        self._normalized_customers_cache: Optional[Dict[int, Dict[str, Any]]] = None

    def connect(self):
        """Establish database connection"""
        if self.connection is None or self.connection.closed:
            try:
                self.connection = psycopg.connect(self.database_url)
                logger.info("Database connection established")
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                raise

    def close(self):
        """Close database connection"""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        """
        Execute a SELECT query and return results

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            List of result tuples
        """
        self.connect()
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.debug(f"Query: {query}")
            logger.debug(f"Params: {params}")
            raise

    def execute_insert(self, query: str, params: tuple = None) -> None:
        """
        Execute an INSERT/UPDATE query

        Args:
            query: SQL query
            params: Query parameters
        """
        self.connect()
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Insert/update failed: {e}")
            logger.debug(f"Query: {query}")
            logger.debug(f"Params: {params}")
            raise

    def get_all_customers(self) -> List[Tuple[int, str]]:
        """
        Get all customers from public.clients table

        Returns:
            List of (customerid, customer_name) tuples
        """
        query = "SELECT customerid, customer FROM public.clients ORDER BY customer"
        try:
            results = self.execute_query(query)
            logger.info(f"Retrieved {len(results)} customers from database")
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve customers: {e}")
            raise

    def _initialize_customer_cache(self) -> Dict[int, Dict[str, Any]]:
        """
        Initialize in-memory cache of normalized customer data.

        Called once on first fuzzy_match_customer() call.
        Cache persists for lifetime of DatabaseHelper instance.

        Performance:
        - One-time cost: ~500ms for 4,724 customers
        - Subsequent matches: ~10ms (from cache)
        - Memory: ~2MB for cache structure

        Returns:
            Dictionary mapping customer_id to normalized data
        """
        from .text_normalizer import (
            remove_accents,
            normalize_business_name,
            normalize_personal_name,
            extract_buying_group_keywords,
            is_personal_name
        )

        logger.info("Initializing customer normalization cache...")
        cache = {}

        all_customers = self.get_all_customers()

        for customer_id, db_customer_name in all_customers:
            # Step 1: Basic normalization (lowercase, remove accents)
            db_name_clean = remove_accents(db_customer_name.lower().strip())

            # Step 2: Detect if personal vs business name
            is_personal = is_personal_name(db_name_clean)

            # Step 3: Apply appropriate normalization
            if is_personal:
                # Personal name: normalize gendered names + sort tokens
                db_name_normalized = normalize_personal_name(db_name_clean)
            else:
                # Business name: apply synonym + legal entity normalization
                db_name_normalized = normalize_business_name(db_name_clean)

            # Step 4: Extract buying group keywords (for business names only)
            db_keywords = extract_buying_group_keywords(db_name_clean) if not is_personal else []

            # Step 5: Store in cache
            cache[customer_id] = {
                "original": db_customer_name,
                "normalized": db_name_normalized,
                "keywords": db_keywords,
                "is_personal": is_personal,
            }

        logger.info(f"Customer cache initialized: {len(cache)} customers cached")
        logger.info(f"  - Personal names: {sum(1 for v in cache.values() if v['is_personal'])}")
        logger.info(f"  - Business names: {sum(1 for v in cache.values() if not v['is_personal'])}")

        return cache

    def fuzzy_match_customer(
        self,
        potential_names: List[str],
        threshold: float = 0.6
    ) -> Tuple[Optional[int], Optional[str], Dict[str, Any]]:
        """
        Fuzzy match customer name against database using in-memory cache.

        Performance improvements:
        - First call: ~500ms (cache initialization) + ~50ms (matching)
        - Subsequent calls: ~10-50ms (cached matching only)
        - 10x-50x faster than previous on-the-fly normalization

        Args:
            potential_names: List of potential customer names from email
            threshold: Minimum similarity score (0.0 to 1.0)

        Returns:
            Tuple of (customer_id, customer_name, match_details) where match_details contains:
            - best_score: float - The highest similarity score found
            - best_match_name: str - The closest matching customer name from database
            - best_match_id: int - The customer ID of the closest match
            - threshold_used: float - The threshold that was applied
            - matched_input: str - The input name that matched best
        """
        from .text_normalizer import (
            remove_accents,
            normalize_business_name,
            normalize_personal_name,
            extract_buying_group_keywords,
            calculate_boosted_similarity,
            calculate_weighted_token_similarity,
            is_personal_name
        )

        # Default match details for when no match is found
        match_details = {
            "best_score": 0.0,
            "best_match_name": None,
            "best_match_id": None,
            "threshold_used": threshold,
            "matched_input": None
        }

        if not potential_names:
            logger.warning("No potential customer names provided for fuzzy matching")
            return None, None, match_details

        # Initialize cache on first call (lazy initialization)
        if self._normalized_customers_cache is None:
            self._normalized_customers_cache = self._initialize_customer_cache()

        # Use cached data
        cache = self._normalized_customers_cache

        best_match = None
        best_score = 0.0
        best_customer_id = None
        best_customer_name = None
        best_base_score = 0.0
        best_boost = 0.0
        best_keywords_matched = []

        # Try to match each potential name against all customers (using cache)
        for potential_name in potential_names:
            # Normalize input: lowercase, strip whitespace, remove accents
            potential_name_clean = remove_accents(potential_name.lower().strip())

            # Detect if input is personal vs business name
            potential_is_personal = is_personal_name(potential_name_clean)

            # Apply appropriate normalization to input
            if potential_is_personal:
                potential_name_normalized = normalize_personal_name(potential_name_clean)
                potential_keywords = []  # No buying group keywords for personal names
            else:
                potential_name_normalized = normalize_business_name(potential_name_clean)
                potential_keywords = extract_buying_group_keywords(potential_name_clean)

            # Match against all cached customers
            for customer_id, cached_data in cache.items():
                db_name_normalized = cached_data["normalized"]
                db_keywords = cached_data["keywords"]
                db_customer_name = cached_data["original"]
                db_is_personal = cached_data["is_personal"]

                # Calculate base similarity using dual scoring strategy:
                # 1. token_set_ratio: excels at word order variations and multi-word matches
                # 2. Jaro-Winkler: excels at character-level typos and abbreviations
                #
                # Conservative approach: Only use Jaro-Winkler as a boost when token score
                # is already reasonably close (>=70%), to avoid false positives from
                # unrelated names that happen to share character patterns.
                token_score = fuzz.token_set_ratio(
                    potential_name_normalized,
                    db_name_normalized
                ) / 100.0

                # Only calculate Jaro-Winkler if token score shows some similarity
                if token_score >= 0.70:
                    jaro_score = calculate_jaro_winkler_similarity(
                        potential_name_normalized,
                        db_name_normalized,
                        prefix_weight=0.15
                    )
                    # Use maximum - catches abbreviations like FAMICAS → FAMICAST
                    base_score = max(token_score, jaro_score)
                else:
                    # Token score too low - likely unrelated names, don't boost
                    base_score = token_score

                # Apply appropriate boosting strategy
                if potential_is_personal and db_is_personal:
                    # Both are personal names: apply weighted token scoring
                    final_score = calculate_weighted_token_similarity(
                        potential_name_normalized,
                        db_name_normalized,
                        base_score
                    )
                    boost = final_score - base_score
                elif not potential_is_personal and not db_is_personal:
                    # Both are business names: apply buying group boost
                    final_score = calculate_boosted_similarity(
                        potential_name_normalized,
                        db_name_normalized,
                        potential_keywords,
                        db_keywords,
                        base_score
                    )
                    boost = final_score - base_score
                else:
                    # Mismatched types (personal vs business): no boost
                    final_score = base_score
                    boost = 0.0

                # Track best match
                if final_score > best_score:
                    best_score = final_score
                    best_match = potential_name
                    best_customer_id = customer_id
                    best_customer_name = db_customer_name
                    best_base_score = base_score
                    best_boost = boost
                    # Calculate matched keywords (only for business names)
                    if potential_keywords and db_keywords:
                        best_keywords_matched = list(set(potential_keywords) & set(db_keywords))
                    else:
                        best_keywords_matched = []

        # Update match details with best match info
        match_details = {
            "best_score": best_score,
            "best_match_name": best_customer_name,
            "best_match_id": best_customer_id,
            "threshold_used": threshold,
            "matched_input": best_match,
            "base_score": best_base_score,
            "buying_group_boost": best_boost,
            "keywords_matched": best_keywords_matched
        }

        # Return best match if above threshold
        if best_score >= threshold:
            # Enhanced logging with normalization details
            if best_boost > 0:
                logger.info(
                    f"Fuzzy match found: '{best_match}' -> '{best_customer_name}' "
                    f"(ID: {best_customer_id}, base_score: {best_base_score:.2f}, "
                    f"boost: +{best_boost:.2f}, final_score: {best_score:.2f}, "
                    f"keywords_matched: {best_keywords_matched})"
                )
            else:
                logger.info(
                    f"Fuzzy match found: '{best_match}' -> '{best_customer_name}' "
                    f"(ID: {best_customer_id}, score: {best_score:.2f})"
                )
            return best_customer_id, best_customer_name, match_details
        else:
            # Enhanced logging for failures
            if best_boost > 0:
                logger.warning(
                    f"No fuzzy match found for: {potential_names} "
                    f"(base_score: {best_base_score:.2f}, boost: +{best_boost:.2f}, "
                    f"final_score: {best_score:.2f}, threshold: {threshold}, "
                    f"closest match: '{best_customer_name}' ID: {best_customer_id}, "
                    f"keywords_matched: {best_keywords_matched})"
                )
            else:
                logger.warning(
                    f"No fuzzy match found for: {potential_names} "
                    f"(best score: {best_score:.2f}, threshold: {threshold}, "
                    f"closest match: '{best_customer_name}' ID: {best_customer_id})"
                )
            return None, None, match_details

    def get_product_families(self) -> List[Tuple[str, str]]:
        """
        Get product families from public.family table

        Returns:
            List of (family_desc, 13DigitPrefix) tuples where brochure_sku = 'Y'
        """
        query = """
            SELECT family_desc, "13DigitPrefix"
            FROM public.family
            WHERE brochure_sku = 'Y'
            ORDER BY family_desc
        """
        try:
            results = self.execute_query(query)
            logger.info(f"Retrieved {len(results)} product families from database")
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve product families: {e}")
            raise

    def get_color_codes(self) -> List[Tuple[str, str]]:
        """
        Get color codes from public.colorcode table

        Returns:
            List of (color_description, colorcode) tuples
        """
        query = """
            SELECT color_description, colorcode
            FROM public.colorcode
            ORDER BY color_description
        """
        try:
            results = self.execute_query(query)
            logger.info(f"Retrieved {len(results)} color codes from database")
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve color codes: {e}")
            raise

    def get_customer_addresses(self, customerid: int) -> List[Dict[str, str]]:
        """
        Get known delivery addresses for a specific customer from v_md_clients_addresses view

        Args:
            customerid: Customer ID to query

        Returns:
            List of dictionaries with keys: street_address, post_code, city, province
            Returns empty list if no addresses found
        """
        query = """
            SELECT street_address,
                   post_code,
                   city,
                   province
            FROM public.v_md_clients_addresses
            WHERE customerid = %s
            ORDER BY street_address
        """
        try:
            results = self.execute_query(query, (customerid,))
            # Convert to list of dictionaries
            addresses = [
                {
                    "street_address": row[0],
                    "post_code": row[1],
                    "city": row[2],
                    "province": row[3]
                }
                for row in results
            ]
            logger.info(f"Retrieved {len(addresses)} addresses for customer {customerid}")
            return addresses
        except Exception as e:
            logger.error(f"Failed to retrieve addresses for customer {customerid}: {e}")
            return []

    def get_clavei_input_data(self) -> Tuple[List[str], List[tuple]]:
        """
        Get all data from AI_Tool_OutputTable_v2 view for Clavei Input CSV export

        Returns:
            Tuple of (column_names, rows) where:
            - column_names: List of column names from the query
            - rows: List of tuples with query results
        """
        query = """
            SELECT "AIOrderNo","LinPed",*
            FROM public."AI_Tool_OutputTable_v2"
            ORDER BY "AIOrderNo","LinPed"
        """
        try:
            self.connect()
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                # Get column names from cursor description
                column_names = [desc[0] for desc in cursor.description]
                results = cursor.fetchall()
                logger.info(f"Retrieved {len(results)} rows from AI_Tool_OutputTable_v2")
                return column_names, results
        except Exception as e:
            logger.error(f"Failed to retrieve Clavei input data: {e}")
            raise

    def query_options_table(
        self,
        family: str,
        color_code: Optional[str] = None,
        size: Optional[str] = None,
        option_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Query public.optionstable for option SKU with family-specific logic

        Family-specific rules:
        - Hermes, Nature, Marco Standard, Marco Personalised, Nature Semicircular:
          Try color match first, fallback to default_size = true
        - Neo: Try color match only, no fallback (return None if no match)
        - Premium: Requires size and type, try color match first, fallback to default_size = true

        Args:
            family: Family description (e.g., "Nature", "Premium")
            color_code: 4-character color code (e.g., "BLCO")
            size: Size for Premium family (e.g., "80")
            option_type: Type for Premium family ("grid" or "cover")

        Returns:
            Option SKU or None if not found
        """
        self.connect()

        # Normalize family name (case-insensitive matching)
        family_lower = family.lower().strip()

        try:
            # Premium family requires size and type
            if family_lower == "premium":
                if not size or not option_type:
                    logger.warning(f"Premium family requires size and type (size={size}, type={option_type})")
                    return None

                # Try with color match first
                if color_code:
                    query = """
                        SELECT sku FROM public.optionstable
                        WHERE LOWER(family) = LOWER(%s)
                        AND color_code = %s
                        AND size = %s
                        AND type = %s
                        LIMIT 1
                    """
                    results = self.execute_query(query, (family, color_code, size, option_type))
                    if results:
                        option_sku = results[0][0]
                        logger.info(f"Options match (Premium): family={family}, color={color_code}, size={size}, type={option_type} -> {option_sku}")
                        return option_sku

                # Fallback to default_size = true
                query = """
                    SELECT sku FROM public.optionstable
                    WHERE LOWER(family) = LOWER(%s)
                    AND size = %s
                    AND type = %s
                    AND default_size = true
                    LIMIT 1
                """
                results = self.execute_query(query, (family, size, option_type))
                if results:
                    option_sku = results[0][0]
                    logger.info(f"Options match (Premium default): family={family}, size={size}, type={option_type} -> {option_sku}")
                    return option_sku

                logger.warning(f"No option SKU found for Premium: family={family}, size={size}, type={option_type}")
                return None

            # Neo family - no fallback to default_size
            elif family_lower == "neo":
                if not color_code:
                    logger.warning(f"Neo family requires color code")
                    return None

                query = """
                    SELECT sku FROM public.optionstable
                    WHERE LOWER(family) = LOWER(%s)
                    AND color_code = %s
                    LIMIT 1
                """
                results = self.execute_query(query, (family, color_code))
                if results:
                    option_sku = results[0][0]
                    logger.info(f"Options match (Neo): family={family}, color={color_code} -> {option_sku}")
                    return option_sku

                logger.warning(f"No option SKU found for Neo: family={family}, color={color_code}")
                return None

            # All other families: Hermes, Nature, Marco Standard, Marco Personalised, Nature Semicircular
            else:
                # Try with color match first
                if color_code:
                    query = """
                        SELECT sku FROM public.optionstable
                        WHERE LOWER(family) = LOWER(%s)
                        AND color_code = %s
                        LIMIT 1
                    """
                    results = self.execute_query(query, (family, color_code))
                    if results:
                        option_sku = results[0][0]
                        logger.info(f"Options match: family={family}, color={color_code} -> {option_sku}")
                        return option_sku

                # Fallback to default_size = true
                query = """
                    SELECT sku FROM public.optionstable
                    WHERE LOWER(family) = LOWER(%s)
                    AND default_size = true
                    LIMIT 1
                """
                results = self.execute_query(query, (family,))
                if results:
                    option_sku = results[0][0]
                    logger.info(f"Options match (default): family={family} -> {option_sku}")
                    return option_sku

                logger.warning(f"No option SKU found for family: {family}")
                return None

        except Exception as e:
            logger.error(f"Failed to query options table: {e}", exc_info=True)
            return None

    def insert_order(self, order_data: Dict[str, Any]) -> bool:
        """
        Insert single order into public.ai_tool_input_table_from_web_app

        Args:
            order_data: Dictionary with keys:
                - orderno (int)
                - customerid (int)
                - 13DigitAlias (str) - SKU
                - orderqty (int)
                - reference_no (str or None)
                - valve (str) - "Yes" or "no"
                - delivery_address (str or None)
                - alternative_cpsd (str or None) - YYYY-MM-DD format
                - entry_id (str or None) - EntryID from email
                - option_sku (str or None) - Option SKU
                - option_qty (int or None) - Option quantity
                - telephone_number (str or None) - Telephone number (only for customer_id 2156)
                - contact_name (str or None) - Contact name (only for NEWKER customers 4891-4895)
                - order_type (str) - Always "text order" for orders from web app

        Returns:
            True if successful, False otherwise
        """
        query = """
            INSERT INTO testing.ai_tool_input_table_from_web_app
            (orderno, customerid, "13DigitAlias", orderqty, reference_no, valve, delivery_address, alternative_cpsd, entry_id, option_sku, option_qty, telephone_number, contact_name, order_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params = (
            order_data.get("orderno"),
            order_data.get("customerid"),
            order_data.get("13DigitAlias"),
            order_data.get("orderqty"),
            order_data.get("reference_no"),
            order_data.get("valve"),
            order_data.get("delivery_address"),
            order_data.get("alternative_cpsd"),
            order_data.get("entry_id"),
            order_data.get("option_sku"),
            order_data.get("option_qty"),
            order_data.get("telephone_number"),
            order_data.get("contact_name"),
            "text order",
        )

        try:
            self.execute_insert(query, params)
            logger.debug(f"Inserted order {order_data.get('orderno')} for customer {order_data.get('customerid')}")
            return True
        except Exception as e:
            logger.error(f"Failed to insert order: {e}")
            return False

    def insert_orders_batch(self, orders_data: List[Dict[str, Any]]) -> bool:
        """
        Insert multiple orders in a single multi-row INSERT statement
        This ensures INSERT triggers see all rows together in one statement

        Args:
            orders_data: List of order dictionaries with keys:
                - orderno, customerid, 13DigitAlias, orderqty, reference_no, valve,
                  delivery_address, alternative_cpsd, entry_id, option_sku, option_qty,
                  telephone_number, contact_name, order_type (always "text order")

        Returns:
            True if all successful, False otherwise
        """
        if not orders_data:
            logger.warning("No orders to insert")
            return True

        self.connect()

        try:
            with self.connection.cursor() as cursor:
                # Build multi-row INSERT statement
                # INSERT INTO table (cols) VALUES (row1), (row2), (row3)...

                # Create placeholders for each row: (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                value_placeholder = "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

                # Create comma-separated list of placeholders for all rows
                values_clause = ", ".join([value_placeholder] * len(orders_data))

                # Build complete query
                query = f"""
                    INSERT INTO testing.ai_tool_input_table_from_web_app
                    (orderno, customerid, "13DigitAlias", orderqty, reference_no, valve, delivery_address, alternative_cpsd, entry_id, option_sku, option_qty, telephone_number, contact_name, order_type, job_id)
                    VALUES {values_clause}
                """

                # Flatten all parameters into single tuple
                # Each order contributes 15 values, so final tuple has 15 * len(orders_data) values
                all_params = []
                for order in orders_data:
                    all_params.extend([
                        order.get("orderno"),
                        order.get("customerid"),
                        order.get("13DigitAlias"),
                        order.get("orderqty"),
                        order.get("reference_no"),
                        order.get("valve"),
                        order.get("delivery_address"),
                        order.get("alternative_cpsd"),
                        order.get("entry_id"),
                        order.get("option_sku"),
                        order.get("option_qty"),
                        order.get("telephone_number"),
                        order.get("contact_name"),
                        "text order",
                        order.get("job_id"),
                    ])

                # Execute single multi-row INSERT
                cursor.execute(query, tuple(all_params))
                self.connection.commit()

                logger.info(f"Successfully inserted {len(orders_data)} orders in single INSERT statement")
                return True

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Batch insert failed: {e}")
            logger.debug(f"Failed to insert {len(orders_data)} orders")
            return False

    def update_job_runs_counts(self, job_id: int) -> bool:
        """
        Update job_runs table with order and order line counts for a specific job

        Args:
            job_id: Job ID to update counts for

        Returns:
            True if successful, False otherwise
        """
        query = """
            UPDATE public.job_runs
            SET
                number_of_orders = (
                    SELECT COUNT(DISTINCT orderno)
                    FROM public.ai_tool_output_table
                    WHERE job_id = %s
                ),
                number_of_order_lines = (
                    SELECT COUNT(*)
                    FROM public.ai_tool_output_table
                    WHERE job_id = %s
                )
            WHERE id = %s
        """

        params = (job_id, job_id, job_id)

        try:
            self.execute_insert(query, params)
            logger.info(f"Updated job_runs counts for job_id {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update job_runs counts for job_id {job_id}: {e}")
            return False

    def save_failure_context(self, job_id: int, contexts: List[Dict[str, Any]]) -> bool:
        """
        Save failure context data to job_runs table

        Args:
            job_id: Job ID to update
            contexts: List of failure context dictionaries

        Returns:
            True if successful, False otherwise
        """
        query = """
            UPDATE public.job_runs
            SET failure_context = %s
            WHERE id = %s
        """

        try:
            self.execute_insert(query, (json.dumps(contexts), job_id))
            logger.info(f"Saved {len(contexts)} failure context(s) for job_id {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save failure context for job_id {job_id}: {e}")
            return False

    def get_failure_context(self, job_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get failure context data for a job

        Args:
            job_id: Job ID to query

        Returns:
            List of failure context dictionaries, or None if not found
        """
        query = """
            SELECT failure_context
            FROM public.job_runs
            WHERE id = %s
        """

        try:
            results = self.execute_query(query, (job_id,))
            if results and results[0][0]:
                return results[0][0]  # JSONB is automatically deserialized by psycopg
            return None
        except Exception as e:
            logger.error(f"Failed to get failure context for job_id {job_id}: {e}")
            return None

    def save_failure_summary(self, job_id: int, summary: str) -> bool:
        """
        Save generated failure summary to job_runs table

        Args:
            job_id: Job ID to update
            summary: AI-generated summary text

        Returns:
            True if successful, False otherwise
        """
        query = """
            UPDATE public.job_runs
            SET failure_summary = %s,
                failure_summary_generated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """

        try:
            self.execute_insert(query, (summary, job_id))
            logger.info(f"Saved failure summary for job_id {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save failure summary for job_id {job_id}: {e}")
            return False

    def get_failure_summary(self, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cached failure summary for a job

        Args:
            job_id: Job ID to query

        Returns:
            Dictionary with 'failure_summary' and 'failure_summary_generated_at', or None if not found
        """
        query = """
            SELECT failure_summary, failure_summary_generated_at
            FROM public.job_runs
            WHERE id = %s
        """

        try:
            results = self.execute_query(query, (job_id,))
            if results and results[0][0]:
                return {
                    "failure_summary": results[0][0],
                    "failure_summary_generated_at": results[0][1]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get failure summary for job_id {job_id}: {e}")
            return None

    def lookup_customer_by_email(self, email_address: str) -> Optional[Tuple[int, str]]:
        """
        Look up customer by email address in email_lookup_for_customer table.
        Used as a fallback when customer name extraction and fuzzy matching fail.

        Args:
            email_address: Email address to look up (case-insensitive)

        Returns:
            Tuple of (customerid, customername) if found, None otherwise
        """
        if not email_address:
            return None

        query = """
            SELECT customerid, customername
            FROM public.email_lookup_for_customer
            WHERE LOWER(emailaddress) = LOWER(%s)
            LIMIT 1
        """

        try:
            results = self.execute_query(query, (email_address,))
            if results:
                customerid, customername = results[0]
                logger.info(f"Email lookup found: {email_address} -> ID={customerid}, Name={customername}")
                return (customerid, customername)
            logger.info(f"Email lookup: no match for {email_address}")
            return None
        except Exception as e:
            logger.error(f"Email lookup failed for {email_address}: {e}")
            return None


# Global instance (lazy initialization)
_db_helper: Optional[DatabaseHelper] = None


def get_db_helper() -> DatabaseHelper:
    """Get or create global database helper instance"""
    global _db_helper
    if _db_helper is None:
        _db_helper = DatabaseHelper()
    return _db_helper

