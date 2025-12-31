"""
Intent Classifier
Categorizes user questions into: HISTORY, ANALYSIS, RECOMMENDATION, AMBIGUOUS
"""
import requests
import json
from typing import Literal

IntentType = Literal["HISTORY", "ANALYSIS", "RECOMMENDATION", "AMBIGUOUS"]

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"


def classify_intent(question: str) -> IntentType:
    """
    Classify user question into one of four categories
    
    Args:
        question: User's natural language question
        
    Returns:
        One of: HISTORY, ANALYSIS, RECOMMENDATION, AMBIGUOUS
    """
    
    prompt = f"""You are a financial query classifier.

ANALYSIS: Questions asking for calculations, totals, averages, comparisons, amounts spent
PRIORITY KEYWORDS (if ANY of these present → ANALYSIS): "how much", "total", "spent", "spending", "average", "cost", "expense"
Examples: 
- 'How much did I spend on food?'
- 'What's my average transaction amount?'
- 'Total spending on entertainment?'
- 'How much did I spend on food and transport?'

HISTORY: Questions asking to list/show/find specific transactions or purchases
Keywords: "show", "list", "find", "display", "buy", "bought", "purchase", "what did i"
Examples: 
- 'Show me food transactions'
- 'List Swiggy orders'
- 'What did I buy in March?'
- 'Find transactions above ₹5000'

RECOMMENDATION: Questions asking for advice, insights, or suggestions
Keywords: "save", "reduce", "advice", "why", "should", "recommend", "overspend", "cut back", "insight"
Examples: 
- 'How can I save money?'
- 'What should I focus on?'
- 'Why did I overspend?'

AMBIGUOUS: Question is unclear or doesn't fit above categories
Examples: 'What about that?', 'More details', 'Huh?'

IMPORTANT: If the question contains "how much", "total", "spent", "spending", or "average", it is ALWAYS ANALYSIS, NOT RECOMMENDATION.

Classify this question: '{question}'

Answer with ONLY the category name (ANALYSIS, HISTORY, RECOMMENDATION, or AMBIGUOUS):"""

    try:
        # Call Ollama
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature = more deterministic
                    "num_predict": 20    # We only need 1 word
                }
            },
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Extract category from response
        category = result['response'].strip().upper()
        
        # Clean up (remove any extra text)
        for valid_cat in ["ANALYSIS", "HISTORY", "RECOMMENDATION", "AMBIGUOUS"]:
            if valid_cat in category:
                return valid_cat
        
        # If we can't parse, default to AMBIGUOUS
        print(f"⚠️  Could not parse category from: {category}")
        return "AMBIGUOUS"
        
    except requests.exceptions.Timeout:
        print("⚠️  Ollama timeout - is the server running?")
        return "AMBIGUOUS"
    except Exception as e:
        print(f"❌ Intent classification error: {e}")
        return "AMBIGUOUS"


# Test function
if __name__ == "__main__":
    # Test cases
    test_questions = [
        "How much did I spend on food?",
        "Show me all transactions above ₹5000",
        "How can I save money on dining?",
        "Compare my September and October spending",
        "What about that thing?",
        "List all Swiggy orders",
        "What's my average monthly spending?",
        "Why did I overspend this month?"
    ]
    
    print("🧪 Testing Intent Classifier\n")
    print("="*60)
    
    for question in test_questions:
        intent = classify_intent(question)
        print(f"Q: {question}")
        print(f"Intent: {intent}\n")