"""
Response Formatter - Converts SQL results to natural language
Template-based for now (no LLM needed), can add LLM polish later
"""

def format_currency(amount):
    """Format amount as Indian Rupees"""
    if amount is None:
        return "₹0"
    return f"₹{abs(float(amount)):,.0f}"


def format_response(intent: str, query_result: dict, filters: dict, question: str) -> dict:
    """
    Format SQL results into natural language response
    
    Args:
        intent: HISTORY | ANALYSIS | RECOMMENDATION | AMBIGUOUS
        query_result: {sql, params, columns, result_type, data}
        filters: Extracted filters
        question: Original question
        
    Returns:
        {
            'answer': str,  # Natural language answer
            'data': list,   # Raw data (for tables)
            'show_table': bool  # Whether to show table in UI
        }
    """
    
    if intent == "AMBIGUOUS":
        return {
            'answer': "I'm not sure what you're asking. Can you rephrase? Try asking things like:\n\n• 'Show me food transactions in October'\n• 'How much did I spend on transport?'\n• 'List Swiggy orders above ₹500'",
            'data': [],
            'show_table': False
        }
    
    # No data returned
    if not query_result or not query_result.get('data'):
        return format_no_results(filters)
    
    data = query_result['data']
    result_type = query_result['result_type']
    
    # ============================================================
    # HISTORY: List of transactions
    # ============================================================
    
    if result_type == "list":
        return format_history_response(data, filters)
    
    # ============================================================
    # ANALYSIS: Aggregated stats
    # ============================================================
    
    elif result_type == "aggregation":
        return format_analysis_response(data, filters)
    
    # ============================================================
    # RECOMMENDATION: Category breakdown for advice
    # ============================================================
    
    elif result_type == "category_breakdown":
        return format_recommendation_response(data, filters)
    
    else:
        return {
            'answer': "I found some results but couldn't format them properly.",
            'data': data,
            'show_table': True
        }


def format_history_response(data, filters):
    """Format transaction list"""
    
    count = len(data)
    
    # Build description
    parts = []
    if filters.get('category'):
        parts.append(filters['category'])
    if filters.get('description_keyword'):
        parts.append(filters['description_keyword'])
    if filters.get('month'):
        month_name = get_month_name(filters['month'])
        parts.append(f"in {month_name}")
    
    description = " ".join(parts) if parts else "matching your criteria"
    
    # Calculate total
    total = sum(float(row['amount']) for row in data)
    
    # Build answer
    answer = f"Found {count} transaction{'s' if count != 1 else ''} {description}.\n\n"
    answer += f"**Total:** {format_currency(total)}\n\n"
    
    if count <= 5:
        # Show transactions inline if few
        answer += "**Transactions:**\n"
        for row in data:
            answer += f"• {row['date']} - {row['description']} - {format_currency(row['amount'])}\n"
        show_table = False
    else:
        answer += f"Showing top {min(count, 50)} results. Click 'View Details' below to see the full list."
        show_table = True
    
    return {
        'answer': answer,
        'data': data,
        'show_table': show_table
    }


def format_analysis_response(data, filters):
    """Format aggregation stats"""
    
    # data is a single row with stats
    row = data[0]
    
    count = row['transaction_count']
    total = row['total_spent']
    avg = row['average_spent']
    min_amt = row['min_spent']
    max_amt = row['max_spent']
    
    # Build description
    parts = []
    if filters.get('category'):
        parts.append(f"on **{filters['category']}**")
    if filters.get('description_keyword'):
        parts.append(f"for **{filters['description_keyword']}**")
    if filters.get('month'):
        month_name = get_month_name(filters['month'])
        parts.append(f"in **{month_name}**")
    
    description = " ".join(parts) if parts else ""
    
    # Build answer
    answer = f"You spent **{format_currency(total)}** {description}.\n\n"
    answer += f"📊 **Stats:**\n"
    answer += f"• Transactions: {count}\n"
    answer += f"• Average: {format_currency(avg)}\n"
    answer += f"• Smallest: {format_currency(min_amt)}\n"
    answer += f"• Largest: {format_currency(max_amt)}\n"
    
    return {
        'answer': answer,
        'data': data,
        'show_table': False
    }


def format_recommendation_response(data, filters):
    """Format category breakdown with recommendations"""
    
    total_spent = sum(float(row['total_spent']) for row in data)
    
    answer = f"Here's your spending breakdown (total: {format_currency(total_spent)}):\n\n"
    
    for row in data:
        category = row['category']
        amount = float(row['total_spent'])
        count = row['transaction_count']
        percentage = (amount / total_spent * 100) if total_spent > 0 else 0
        
        answer += f"**{category}** - {format_currency(amount)} ({percentage:.0f}%) - {count} transactions\n"
    
    # Add simple recommendation
    if data:
        top_category = data[0]['category']
        top_amount = float(data[0]['total_spent'])
        
        answer += f"\n💡 **Insight:** Your highest spending is on **{top_category}** ({format_currency(top_amount)}). "
        answer += get_recommendation_text(top_category)
    
    return {
        'answer': answer,
        'data': data,
        'show_table': False
    }


def format_no_results(filters):
    """Format response when no results found"""
    
    parts = []
    if filters.get('category'):
        parts.append(f"in category '{filters['category']}'")
    if filters.get('month'):
        month_name = get_month_name(filters['month'])
        parts.append(f"in {month_name}")
    if filters.get('description_keyword'):
        parts.append(f"matching '{filters['description_keyword']}'")
    if filters.get('min_amount') or filters.get('max_amount'):
        if filters.get('min_amount') and filters.get('max_amount'):
            parts.append(f"between {format_currency(filters['min_amount'])} and {format_currency(filters['max_amount'])}")
        elif filters.get('min_amount'):
            parts.append(f"above {format_currency(filters['min_amount'])}")
        else:
            parts.append(f"below {format_currency(filters['max_amount'])}")
    
    criteria = " ".join(parts) if parts else "matching your criteria"
    
    return {
        'answer': f"No transactions found {criteria}.",
        'data': [],
        'show_table': False
    }


def get_month_name(month_str):
    """Convert YYYY-MM to readable month"""
    months = {
        '01': 'January', '02': 'February', '03': 'March', '04': 'April',
        '05': 'May', '06': 'June', '07': 'July', '08': 'August',
        '09': 'September', '10': 'October', '11': 'November', '12': 'December'
    }
    
    try:
        year, month = month_str.split('-')
        return f"{months[month]} {year}"
    except:
        return month_str


def get_recommendation_text(category):
    """Get recommendation based on top spending category"""
    
    recommendations = {
        'Food & Dining': "Consider cooking more meals at home to save money.",
        'Transport': "Look into monthly passes or carpooling to reduce costs.",
        'Shopping': "Set a monthly budget and track discretionary purchases.",
        'Entertainment': "Review subscriptions and cancel unused services.",
        'Bills & Utilities': "Consider energy-saving measures to reduce bills.",
        'Groceries': "Plan weekly meals and make shopping lists to avoid waste.",
    }
    
    return recommendations.get(category, "Track this category closely to identify savings opportunities.")


# ============================================================
# TESTS
# ============================================================

if __name__ == "__main__":
    
    print("🧪 Testing Response Formatter")
    print("=" * 70)
    
    # Test 1: History with few results
    print("\n1. HISTORY (few results):")
    data = [
        {'date': '2024-10-15', 'description': 'Swiggy Order', 'amount': 450, 'category': 'Food & Dining', 'source': 'BANK'},
        {'date': '2024-10-12', 'description': 'Zomato', 'amount': 380, 'category': 'Food & Dining', 'source': 'BANK'},
    ]
    result = format_response(
        intent="HISTORY",
        query_result={'result_type': 'list', 'data': data},
        filters={'category': 'Food & Dining', 'month': '2024-10'},
        question="Show me food transactions in October"
    )
    print(result['answer'])
    print(f"Show table: {result['show_table']}")
    
    # Test 2: Analysis
    print("\n" + "=" * 70)
    print("2. ANALYSIS:")
    data = [
        {
            'transaction_count': 15,
            'total_spent': 6500,
            'average_spent': 433,
            'min_spent': 120,
            'max_spent': 850
        }
    ]
    result = format_response(
        intent="ANALYSIS",
        query_result={'result_type': 'aggregation', 'data': data},
        filters={'category': 'Food & Dining', 'month': '2024-10'},
        question="How much did I spend on food in October?"
    )
    print(result['answer'])
    
    # Test 3: Recommendation
    print("\n" + "=" * 70)
    print("3. RECOMMENDATION:")
    data = [
        {'category': 'Food & Dining', 'transaction_count': 25, 'total_spent': 8500},
        {'category': 'Transport', 'transaction_count': 18, 'total_spent': 3200},
        {'category': 'Shopping', 'transaction_count': 12, 'total_spent': 2800},
    ]
    result = format_response(
        intent="RECOMMENDATION",
        query_result={'result_type': 'category_breakdown', 'data': data},
        filters={},
        question="What categories am I overspending on?"
    )
    print(result['answer'])
    
    # Test 4: No results
    print("\n" + "=" * 70)
    print("4. NO RESULTS:")
    result = format_response(
        intent="HISTORY",
        query_result={'result_type': 'list', 'data': []},
        filters={'category': 'Entertainment', 'month': '2024-10'},
        question="Show me entertainment in October"
    )
    print(result['answer'])
    
    # Test 5: Ambiguous
    print("\n" + "=" * 70)
    print("5. AMBIGUOUS:")
    result = format_response(
        intent="AMBIGUOUS",
        query_result=None,
        filters={},
        question="What about that?"
    )
    print(result['answer'])
    
    print("\n" + "=" * 70)
    print("✅ Response formatter working!")
    print("=" * 70)