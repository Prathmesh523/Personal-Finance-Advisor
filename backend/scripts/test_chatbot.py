#!/usr/bin/env python3
"""
Chatbot Backend Test Script
Tests intent classification, filter extraction, and response quality
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1/chat"

# Color codes for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_separator():
    print(f"\n{Colors.CYAN}{'='*80}{Colors.END}")

def print_question(num, question):
    print_separator()
    print(f"{Colors.BOLD}{Colors.HEADER}Q{num}: {question}{Colors.END}")
    print_separator()

def print_response(data):
    """Pretty print chatbot response"""
    print(f"\n{Colors.BLUE}Intent:{Colors.END} {data.get('intent', 'N/A')}")
    print(f"{Colors.BLUE}Filters:{Colors.END} {json.dumps(data.get('filters', {}), indent=2)}")
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}Answer:{Colors.END}")
    print(data.get('answer', 'No answer'))
    
    if data.get('show_table'):
        row_count = len(data.get('data', []))
        print(f"\n{Colors.YELLOW}📊 [Table with {row_count} rows]{Colors.END}")
        if row_count > 0 and row_count <= 3:
            print(f"{Colors.YELLOW}Sample data:{Colors.END}")
            for row in data.get('data', [])[:3]:
                print(f"  {row}")

def test_question(num, question, category=""):
    """Test a single question"""
    if category:
        print(f"\n{Colors.BOLD}{Colors.CYAN}### {category} ###{Colors.END}")
    
    print_question(num, question)
    
    try:
        response = requests.post(BASE_URL, params={"question": question, "user_id": 1}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print_response(data)
            return True
        else:
            print(f"{Colors.RED}❌ HTTP {response.status_code}: {response.text}{Colors.END}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}❌ Connection Error - Is the backend running?{Colors.END}")
        return False
    except Exception as e:
        print(f"{Colors.RED}❌ Error: {e}{Colors.END}")
        return False

def main():
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("="*80)
    print("🤖 FINANCE CHATBOT - BACKEND TEST SUITE")
    print("="*80)
    print(f"{Colors.END}")
    print(f"Testing endpoint: {BASE_URL}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_count = 0
    success_count = 0
    
    # =================================================================
    # HISTORY INTENT TESTS (List/Show Transactions)
    # =================================================================
    
    # questions = [
    #     ("HISTORY - Basic Category", "Show me all my food expenses"),
    #     ("HISTORY - Specific Merchant", "What did I spend on Swiggy?"),
    #     ("HISTORY - Subscription", "List my Netflix transactions"),
    #     ("HISTORY - Amount Filter", "Show me transactions above ₹5000"),
    #     ("HISTORY - Month + Category", "Find all my Uber rides in February"),
    #     ("HISTORY - Amount Range", "Show me grocery shopping below ₹500"),
    #     ("HISTORY - Multiple Keywords", "Show me all Zomato and Swiggy orders"),
    #     ("HISTORY - Month Only", "What did I buy in March?"),
    #     ("HISTORY - Category + Amount", "Show food expenses above ₹1000"),
    #     ("HISTORY - All Transactions", "List all my transactions"),
    # ]
    
    # for category, question in questions:
    #     test_count += 1
    #     if test_question(test_count, question, category if test_count in [1, 11, 19] else ""):
    #         success_count += 1
    
    # =================================================================
    # ANALYSIS INTENT TESTS (Calculations/Aggregations)
    # =================================================================
    
    # questions = [
    #     ("ANALYSIS - Category Total", "How much did I spend on food?"),
    #     ("ANALYSIS - Month Total", "What's my total spending in February?"),
    #     ("ANALYSIS - Category + Month", "How much did I spend on transport in March?"),
    #     ("ANALYSIS - Average", "What's my average transaction amount?"),
    #     ("ANALYSIS - Specific Category", "How much did I spend on entertainment?"),
    #     ("ANALYSIS - Groceries", "What's my total spending on groceries?"),
    #     ("ANALYSIS - Overall", "How much did I spend in total?"),
    #     ("ANALYSIS - Multiple Categories", "How much did I spend on food and transport?"),
    # ]
    
    # for category, question in questions:
    #     test_count += 1
    #     if test_question(test_count, question, category if test_count == 11 else ""):
    #         success_count += 1
    
    # =================================================================
    # RECOMMENDATION INTENT TESTS (Advice/Insights)
    # =================================================================
    
    questions = [
        ("RECOMMENDATION - General", "Where am I overspending?"),
        ("RECOMMENDATION - Savings", "How can I save money?"),
        ("RECOMMENDATION - Top Category", "What's my biggest expense category?"),
        ("RECOMMENDATION - Advice", "Give me spending advice"),
        ("RECOMMENDATION - Why Question", "Why is my food spending so high?"),
        ("RECOMMENDATION - Cut Back", "What should I cut back on?"),
        ("RECOMMENDATION - Insights", "What insights do you have about my spending?"),
    ]
    
    for category, question in questions:
        test_count += 1
        if test_question(test_count, question, category if test_count == 19 else ""):
            success_count += 1
    
    # =================================================================
    # EDGE CASES & TRICKY QUESTIONS
    # =================================================================
    
    # print(f"\n{Colors.BOLD}{Colors.CYAN}### EDGE CASES & TRICKY QUESTIONS ###{Colors.END}")
    
    # edge_cases = [
    #     "Show me Zomato orders above ₹1000 in February",
    #     "How much did I spend between ₹500 and ₹2000?",
    #     "List my subscriptions",
    #     "Show me all settlements",
    #     "What are my recurring expenses?",
    #     "Find transactions with 'transfer' in description",
    # ]
    
    # for question in edge_cases:
    #     test_count += 1
    #     if test_question(test_count, question):
    #         success_count += 1
    
    # =================================================================
    # SUMMARY
    # =================================================================
    
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"{Colors.END}")
    
    print(f"Total Questions: {test_count}")
    print(f"{Colors.GREEN}Successful: {success_count}{Colors.END}")
    
    if test_count > success_count:
        print(f"{Colors.RED}Failed: {test_count - success_count}{Colors.END}")
    
    accuracy = (success_count / test_count * 100) if test_count > 0 else 0
    
    if accuracy >= 90:
        print(f"\n{Colors.GREEN}✅ Accuracy: {accuracy:.1f}% - EXCELLENT{Colors.END}")
    elif accuracy >= 75:
        print(f"\n{Colors.YELLOW}⚠️  Accuracy: {accuracy:.1f}% - GOOD (needs improvement){Colors.END}")
    else:
        print(f"\n{Colors.RED}❌ Accuracy: {accuracy:.1f}% - NEEDS WORK{Colors.END}")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == "__main__":
    main()