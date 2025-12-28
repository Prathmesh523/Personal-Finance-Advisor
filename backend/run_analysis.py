#!/usr/bin/env python3
"""
Financial Analysis Pipeline
Assumes: Docker, DB, and Consumer are already running
"""
import subprocess
import time
import os
import sys

def run_step(description, command):
    """Execute command and show output"""
    print(f"\n{'='*60}")
    print(f"⚙️  {description}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("⚠️  Warnings/Errors:")
        print(result.stderr)
    
    if result.returncode == 0:
        print(f"✅ {description} - COMPLETE")
        return True
    else:
        print(f"❌ {description} - FAILED (Exit code: {result.returncode})")
        return False

def main():
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║        FINANCIAL ANALYSIS PIPELINE v1.0              ║
    ║          Settlement + Linking + Analytics            ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    # Step 0: Get month/year from user
    print("\n📅 STEP 1: SELECT MONTH TO ANALYZE")
    print("="*60)
    
    try:
        year = int(input("Enter year (e.g., 2025): "))
        month = int(input("Enter month (1-12): "))
        
        if month < 1 or month > 12:
            print("❌ Invalid month. Must be 1-12.")
            sys.exit(1)
            
    except ValueError:
        print("❌ Invalid input. Please enter numbers only.")
        sys.exit(1)
    
    print(f"\n✅ Selected: {year}-{month:02d}")
    
    # Create upload session
    print("\n📦 Creating upload session...")
    from app.services.session_manager import create_upload_session, update_session_counts, check_duplicate_session
    
    # Check for duplicates
    month_str = f"{year}-{month:02d}"
    duplicate_check = check_duplicate_session(user_id=1, selected_month=month_str)
    
    if duplicate_check['exists']:
        print(f"\n⚠️  WARNING: {month_str} already analyzed!")
        print(f"   Session ID: {duplicate_check['session_id']}")
        print(f"   Transactions: {duplicate_check['transaction_count']}")
        print(f"   Date: {duplicate_check['created_at']}")
        
        choice = input("\nOptions:\n  1. View existing analysis\n  2. Replace with new upload\n  3. Cancel\nChoice (1/2/3): ")
        
        if choice == '1':
            print(f"\n💡 Use session_id '{duplicate_check['session_id']}' to view results")
            print("   (Analytics module coming soon)")
            sys.exit(0)
        elif choice == '2':
            print("\n⚠️  Replacing existing data...")
            # Delete old session data
            from app.database.connection import get_db_connection
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM transactions WHERE upload_session_id = %s", (duplicate_check['session_id'],))
            cur.execute("DELETE FROM upload_sessions WHERE id = %s", (duplicate_check['session_id'],))
            conn.commit()
            cur.close()
            conn.close()
            print("✅ Old data deleted")
        else:
            print("❌ Upload cancelled")
            sys.exit(0)
    
    # Create new session
    session_info = create_upload_session(
        user_id=1,
        selected_month=month,
        selected_year=year
    )
    
    session_id = session_info['session_id']
    start_date = session_info['start_date']
    end_date = session_info['end_date']
    
    print(f"\n✅ Session created: {session_id}")
    print(f"   Date range: {start_date} to {end_date}")
    
    # Pre-flight checks
    print("\n🔍 STEP 2: PRE-FLIGHT CHECKS")
    print("="*60)
    
    required_files = [
        'data/raw_uploads/bank_statement.csv',
        'data/raw_uploads/splitwise_october.csv'
    ]
    
    missing = [f for f in required_files if not os.path.exists(f)]
    
    if missing:
        print("\n❌ ERROR: Missing files:")
        for f in missing:
            print(f"   - {f}")
        sys.exit(1)
    
    print("✅ CSV files found")
    
    # Check if services are running
    print("\n⚠️  PREREQUISITES (Must be running):")
    print("   1. Docker: docker-compose up -d")
    print("   2. Database: python init_db.py")
    print("   3. RabbitMQ Consumer: python -m app.etl.consumers.data_processor")
    
    input("\n👉 Press ENTER when ready to proceed...")
    
    # Phase 1: Data Ingestion
    print("\n" + "📥 STEP 3: DATA INGESTION".center(60, "="))
    
    bank_result = None
    splitwise_result = None
    
    # Bank Producer
    if not run_step(
        "Bank Producer",
        f"python -m app.etl.producers.bank_producer {session_id} {start_date} {end_date}"
    ):
        print("❌ Bank producer failed. Exiting.")
        sys.exit(1)
    
    # Splitwise Producer
    if not run_step(
        "Splitwise Producer",
        f"python -m app.etl.producers.splitwise_producer {session_id} {start_date} {end_date}"
    ):
        print("❌ Splitwise producer failed. Exiting.")
        sys.exit(1)
    
    # Wait for consumer
    print("⏳ Waiting 5 seconds for messages to be processed...")
    for i in range(5, 0, -1):
        print(f"   {i}...", end='\r')
        time.sleep(1)
    print("   ✅ Consumer should have processed messages")
    
    # Get transaction counts from DB
    print("\n📊 Checking processed transactions...")
    from app.database.connection import get_db_connection
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            source,
            COUNT(*) as count
        FROM transactions
        WHERE upload_session_id = %s
        GROUP BY source
    """, (session_id,))
    
    results = cur.fetchall()
    bank_count = 0
    splitwise_count = 0
    
    for source, count in results:
        if source == 'BANK':
            bank_count = count
        elif source == 'SPLITWISE':
            splitwise_count = count
    
    cur.close()
    conn.close()
    
    print(f"   Bank: {bank_count} transactions")
    print(f"   Splitwise: {splitwise_count} transactions")
    
    if bank_count == 0 and splitwise_count == 0:
        print("\n❌ ERROR: No transactions processed!")
        print("   Check if dates in CSVs match selected month")
        sys.exit(1)
    
    # Update session counts
    update_session_counts(session_id, bank_count, splitwise_count, 0)
    
    # Phase 2: Analysis
    print("\n" + "🧠 STEP 4: INTELLIGENT ANALYSIS".center(60, "="))
    
    # Run analysis pipeline with session_id
    if not run_step(
        "Full Analysis Pipeline",
        f"python -c \"from app.services.linker import run_full_pipeline; run_full_pipeline('{session_id}')\""
    ):
        print("\n❌ Analysis failed. Check errors above.")
        sys.exit(1)
    
    # Summary
    print("\n" + "="*60)
    print("🎉 PIPELINE COMPLETE!")
    print("="*60)
    print(f"\n📊 Analysis Summary for {month_str}:")
    print(f"   Session ID: {session_id}")
    print(f"   Date Range: {start_date} to {end_date}")
    print(f"   Transactions Processed: {bank_count + splitwise_count}")
    
    print("\n✅ What happened:")
    print("   ✅ Data ingested and filtered by selected month")
    print("   ✅ Settlements detected and marked")
    print("   ✅ Transactions linked (Bank ↔ Splitwise)")
    print("   ✅ Other transfers categorized")
    
    print("\n💡 Next Steps:")
    print("   1. Check results: python test_settlement.py")
    print(f"   2. Query database for session: {session_id}")
    print("   3. Stop consumer: Ctrl+C in consumer terminal")
    print("   4. Analyze different month: python run_analysis.py")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(1)