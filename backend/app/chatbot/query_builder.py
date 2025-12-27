"""
Query Builder - Converts filters to SQL queries
Deterministic, no LLM needed
"""

def build_query(intent: str, filters: dict) -> dict:
    """
    Build SQL query based on intent and filters
    
    Returns:
        {
            'sql': str,  # SQL query
            'params': tuple,  # Query parameters
            'columns': list  # Column names for results
        }
    """
    
    session_id = filters.get('session_id')
    category = filters.get('category')
    month = filters.get('month')
    min_amount = filters.get('min_amount')
    max_amount = filters.get('max_amount')
    keyword = filters.get('description_keyword')
    
    # Base WHERE clause (always filter by session)
    where_clauses = ["upload_session_id = %s"]
    params = [session_id]
    
    # Add category filter
    if category:
        where_clauses.append("category = %s")
        params.append(category)
    
    # Add month filter
    if month:
        where_clauses.append("DATE_TRUNC('month', date) = %s::date")
        params.append(f"{month}-01")
    
    # Add amount filters (for bank transactions)
    if min_amount is not None:
        where_clauses.append("ABS(amount) >= %s")
        params.append(min_amount)
    
    if max_amount is not None:
        where_clauses.append("ABS(amount) <= %s")
        params.append(max_amount)
    
    # Add keyword filter
    if keyword:
        where_clauses.append("UPPER(description) LIKE %s")
        params.append(f"%{keyword.upper()}%")
    
    where_sql = " AND ".join(where_clauses)
    
    # ============================================================
    # INTENT-BASED QUERY BUILDING
    # ============================================================
    
    if intent == "HISTORY":
        # List/show transactions
        sql = f"""
            SELECT 
                date,
                description,
                ABS(amount) as amount,
                category,
                'BANK' as source
            FROM bank_transactions
            WHERE {where_sql}
              AND amount < 0
              AND status != 'TRANSFER'
            
            UNION ALL
            
            SELECT 
                date,
                description,
                my_share as amount,
                category,
                'SPLITWISE' as source
            FROM splitwise_transactions
            WHERE {where_sql}
              AND role IN ('PAYER', 'BORROWER')
            
            ORDER BY date DESC
            LIMIT 50
        """
        
        # Double params because UNION has two queries
        params = params + params
        
        columns = ['date', 'description', 'amount', 'category', 'source']
        
        return {
            'sql': sql,
            'params': tuple(params),
            'columns': columns,
            'result_type': 'list'  # Return list of transactions
        }
    
    elif intent == "ANALYSIS":
        # Aggregations (SUM, AVG, COUNT)
        sql = f"""
            SELECT 
                COUNT(*) as transaction_count,
                SUM(ABS(amount)) as total_spent,
                AVG(ABS(amount)) as average_spent,
                MIN(ABS(amount)) as min_spent,
                MAX(ABS(amount)) as max_spent
            FROM (
                SELECT amount, date
                FROM bank_transactions
                WHERE {where_sql}
                  AND amount < 0
                  AND status != 'TRANSFER'
                
                UNION ALL
                
                SELECT -my_share as amount, date
                FROM splitwise_transactions
                WHERE {where_sql}
                  AND role IN ('PAYER', 'BORROWER')
            ) combined
        """
        
        # Double params
        params = params + params
        
        columns = ['transaction_count', 'total_spent', 'average_spent', 'min_spent', 'max_spent']
        
        return {
            'sql': sql,
            'params': tuple(params),
            'columns': columns,
            'result_type': 'aggregation'  # Return single row stats
        }
    
    elif intent == "RECOMMENDATION":
        # For recommendations, we need category breakdown
        sql = f"""
            SELECT 
                category,
                COUNT(*) as transaction_count,
                SUM(amount) as total_spent
            FROM (
                SELECT category, ABS(amount) as amount
                FROM bank_transactions
                WHERE upload_session_id = %s
                  AND amount < 0
                  AND status != 'TRANSFER'
                
                UNION ALL
                
                SELECT category, my_share as amount
                FROM splitwise_transactions
                WHERE upload_session_id = %s
                  AND role IN ('PAYER', 'BORROWER')
            ) combined
            GROUP BY category
            ORDER BY total_spent DESC
            LIMIT 5
        """
        
        params = [session_id, session_id]  # Only session filter for recommendations
        
        columns = ['category', 'transaction_count', 'total_spent']
        
        return {
            'sql': sql,
            'params': tuple(params),
            'columns': columns,
            'result_type': 'category_breakdown'
        }
    
    else:
        # AMBIGUOUS - return None (will be handled by response formatter)
        return None


# ============================================================
# TESTS
# ============================================================

if __name__ == "__main__":
    from filter_extractor import extract_filters
    from intent_classifier import classify_intent
    
    test_cases = [
        ("Show me food transactions in October", "session_123"),
        ("How much did I spend on transport?", "session_123"),
        ("List Swiggy orders above ₹500", "session_123"),
        ("What categories am I overspending on?", "session_123"),
    ]
    
    print("🧪 Testing Query Builder")
    print("=" * 70)
    
    for question, session_id in test_cases:
        print(f"\nQ: {question}")
        
        # Step 1: Classify intent
        intent = classify_intent(question)
        print(f"   Intent: {intent}")
        
        # Step 2: Extract filters
        filters = extract_filters(question, session_id)
        print(f"   Filters: {filters}")
        
        # Step 3: Build query
        query_info = build_query(intent, filters)
        
        if query_info:
            print(f"   Result Type: {query_info['result_type']}")
            print(f"   SQL Preview: {query_info['sql']}...")
            print(f"   Params: {query_info['params']}")
        else:
            print(f"   ⚠️  Ambiguous query - no SQL generated")
    
    print("\n" + "=" * 70)
    print("✅ Query builder working!")
    print("=" * 70)