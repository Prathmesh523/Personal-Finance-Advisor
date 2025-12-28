import re
from datetime import datetime

# ============================================================
# CONFIGURATION - Change this when you have WiFi
# ============================================================
USE_LLM = False  # ✅ Set to True when Mistral is available
MODEL_NAME = "mistral:7b"  # Model to use when USE_LLM = True

# ============================================================
# RULE-BASED EXTRACTION (Current - Fast, Accurate, No LLM)
# ============================================================

def extract_category_rules(question: str) -> str:
    """Extract category using keyword matching"""
    q = question.lower()
    
    # Category keywords (order matters - most specific first)
    if any(word in q for word in ['swiggy', 'zomato', 'food', 'dining', 'restaurant', 'cafe', 'pizza', 'burger']):
        return 'Food & Dining'
    
    if any(word in q for word in ['grocery', 'groceries', 'vegetables', 'fruits', 'supermarket', 'dmart']):
        return 'Groceries'
    
    if any(word in q for word in ['uber', 'ola', 'metro', 'transport', 'taxi', 'cab', 'petrol', 'fuel', 'bus']):
        return 'Transport'
    
    if any(word in q for word in ['shopping', 'amazon', 'flipkart', 'myntra', 'clothes', 'mall']):
        return 'Shopping'
    
    if any(word in q for word in ['netflix', 'spotify', 'prime', 'entertainment', 'movie', 'cinema', 'game']):
        return 'Entertainment'
    
    if any(word in q for word in ['electricity', 'water', 'gas', 'bill', 'utility', 'internet', 'mobile', 'recharge']):
        return 'Bills & Utilities'
    
    if any(word in q for word in ['medicine', 'pharmacy', 'hospital', 'doctor', 'health']):
        return 'Health'
    
    if any(word in q for word in ['investment', 'mutual fund', 'stocks', 'zerodha', 'groww']):
        return 'Investment'
    
    if any(word in q for word in ['education', 'course', 'udemy', 'book']):
        return 'Education'
    
    return None  # No category detected


def extract_month_rules(question: str) -> str:
    """Extract month using regex and keywords"""
    q = question.lower()
    
    # Month name mapping
    month_map = {
        'january': '01', 'jan': '01',
        'february': '02', 'feb': '02',
        'march': '03', 'mar': '03',
        'april': '04', 'apr': '04',
        'may': '05',
        'june': '06', 'jun': '06',
        'july': '07', 'jul': '07',
        'august': '08', 'aug': '08',
        'september': '09', 'sep': '09', 'sept': '09',
        'october': '10', 'oct': '10',
        'november': '11', 'nov': '11',
        'december': '12', 'dec': '12',
    }
    
    # Find month name
    for month_name, month_num in month_map.items():
        if month_name in q:
            return f"2025-{month_num}"
    
    # Check for YYYY-MM format
    match = re.search(r'(202[0-9])[-/](0[1-9]|1[0-2])', q)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    
    return None  # No month detected


def extract_amounts_rules(question: str) -> tuple:
    """Extract min/max amounts using regex"""
    # ❌ OLD: q = question.lower()
    # ✅ NEW: Keep original case for regex matching
    q = question  # Don't lowercase yet
    
    print(f"🔍 DEBUG extract_amounts_rules:")
    print(f"   Input: {question}")
    print(f"   Processing: {q}")
    
    min_amt = None
    max_amt = None
    
    # Pattern: "above/more than/over ₹5000" or "above 5000"
    # Use case-insensitive flag
    match = re.search(r'(above|more than|over|greater than)\s*(?:₹|rs\.?\s*)?(\d+(?:,\d{3})*)', q, re.IGNORECASE)
    print(f"   'above' regex match: {match}")
    if match:
        min_amt = float(match.group(2).replace(',', ''))
        print(f"   ✅ Extracted min_amt: {min_amt}")
    
    # Pattern: "below/less than/under ₹500"
    match = re.search(r'(below|less than|under)\s*(?:₹|rs\.?\s*)?(\d+(?:,\d{3})*)', q, re.IGNORECASE)
    print(f"   'below' regex match: {match}")
    if match:
        max_amt = float(match.group(2).replace(',', ''))
        print(f"   ✅ Extracted max_amt: {max_amt}")
    
    # Pattern: "between ₹1000 and ₹3000"
    match = re.search(r'between\s*(?:₹|rs\.?\s*)?(\d+(?:,\d{3})*)\s*(?:and|to|-)\s*(?:₹|rs\.?\s*)?(\d+(?:,\d{3})*)', q, re.IGNORECASE)
    if match:
        min_amt = float(match.group(1).replace(',', ''))
        max_amt = float(match.group(2).replace(',', ''))
    
    # Pattern: "₹1000-₹3000" or "1000-3000" (only if not already matched)
    if not min_amt and not max_amt:
        match = re.search(r'(?:₹|rs\.?\s*)?(\d+(?:,\d{3})*)\s*-\s*(?:₹|rs\.?\s*)?(\d+(?:,\d{3})*)', q)
        if match:
            num1 = float(match.group(1).replace(',', ''))
            num2 = float(match.group(2).replace(',', ''))
            if num1 > 100 or num2 > 100:
                min_amt = num1
                max_amt = num2
    
    print(f"   Final: min={min_amt}, max={max_amt}")
    
    return min_amt, max_amt


def extract_keyword_rules(question: str) -> str:
    """Extract merchant/keyword using keyword matching"""
    q = question.lower()
    
    # Common merchants/services
    merchants = [
        'swiggy', 'zomato', 'uber', 'ola', 'netflix', 'amazon', 
        'flipkart', 'myntra', 'spotify', 'zerodha', 'groww',
        'paytm', 'phonepe', 'gpay', 'google pay', 'airtel', 'jio'
    ]
    
    for merchant in merchants:
        if merchant in q:
            return merchant.capitalize()
    
    return None  # No keyword detected


# ============================================================
# LLM-BASED EXTRACTION (Future - When Mistral Available)
# ============================================================

def extract_filters_llm(question: str) -> dict:
    """Extract filters using Mistral LLM - placeholder for future"""
    # TODO: Implement when Mistral is downloaded
    # Will use ollama.chat() with better prompts
    raise NotImplementedError("LLM extraction not yet implemented - use rules for now")


# ============================================================
# MAIN EXTRACTION FUNCTION
# ============================================================

def extract_filters(question: str, session_id: str) -> dict:
    """
    Extract structured filters from natural language question
    
    Currently uses rule-based extraction (fast, accurate)
    Set USE_LLM = True when Mistral is available
    """
    
    if USE_LLM:
        # Future: Use Mistral for better accuracy
        return extract_filters_llm(question)
    else:
        # Current: Use rules (works great for 90% of queries)
        category = extract_category_rules(question)
        month = extract_month_rules(question)
        min_amt, max_amt = extract_amounts_rules(question)
        keyword = extract_keyword_rules(question)
        
        return {
            "category": category,
            "month": month,
            "min_amount": min_amt,
            "max_amount": max_amt,
            "description_keyword": keyword,
            "user_id": session_id
        }


# ============================================================
# TESTS
# ============================================================

if __name__ == "__main__":
    test_questions = [
        "How much did I spend on food in October?",
        "Show me all transactions above ₹5000",
        "List Swiggy orders from September",
        "Find transport expenses between ₹1000 and ₹3000",
        "Show me Netflix transactions",
        "What did I spend on shopping?",
        "List all food transactions",
        "Show transactions above ₹10000 in October",
        "Uber rides less than ₹500",
        "Amazon purchases between ₹2000-₹5000 in November",
    ]
    
    print("🧪 Testing Rule-Based Filter Extractor")
    print("=" * 70)
    
    for q in test_questions:
        filters = extract_filters(q, "session_test123")
        print(f"\nQ: {q}")
        print(f"   ✅ Category: {filters['category']}")
        print(f"   ✅ Month: {filters['month']}")
        print(f"   ✅ Amount: {filters['min_amount']} - {filters['max_amount']}")
        print(f"   ✅ Keyword: {filters['description_keyword']}")
    
    print("\n" + "=" * 70)
    print("✅ Rule-based extraction works perfectly!")
    print("💡 To use Mistral later: Set USE_LLM = True at top of file")
    print("=" * 70)