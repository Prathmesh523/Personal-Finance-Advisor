import os
import threading
from datetime import datetime
from pathlib import Path
from app.services.session_manager import create_upload_session, update_session_counts, mark_session_complete
from app.etl.producers.bank_producer import process_bank_file
from app.etl.producers.splitwise_producer import process_splitwise_file
from app.services.linker import run_full_pipeline
from app.database.connection import get_db_connection

# Directory for uploaded files
UPLOAD_DIR = Path("data/raw_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def save_uploaded_file(file, session_id: str, file_type: str) -> str:
    """
    Save uploaded file to disk
    
    Args:
        file: UploadFile object from FastAPI
        session_id: Session identifier
        file_type: 'bank' or 'splitwise'
    
    Returns:
        Path to saved file
    """
    filename = f"{session_id}_{file_type}.csv"
    filepath = UPLOAD_DIR / filename
    
    # Save file
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    
    return str(filepath)


def run_analysis_pipeline(session_id: str, bank_filepath: str, splitwise_filepath: str, 
                          start_date: str, end_date: str):
    """
    Run the complete analysis pipeline in background
    This function runs in a separate thread
    """
    try:
        print(f"🚀 Starting analysis for session: {session_id}")
        
        # Step 1: Process bank file
        print("📥 Processing bank file...")
        bank_result = process_bank_file(bank_filepath, session_id, start_date, end_date)
        
        if bank_result['status'] == 'error':
            update_session_status(session_id, 'failed', str(bank_result.get('message')))
            return
        
        # Step 2: Process splitwise file
        print("📥 Processing splitwise file...")
        splitwise_result = process_splitwise_file(splitwise_filepath, session_id, start_date, end_date)
        
        if splitwise_result['status'] == 'error':
            update_session_status(session_id, 'failed', str(splitwise_result.get('message')))
            return
        
        # Step 3: Wait for consumer to process (Kafka messages)
        print("⏳ Waiting for messages to be processed...")
        import time
        time.sleep(8)  # Give consumer time to process
        
        # Step 4: Update session counts
        bank_count = bank_result['processed']
        splitwise_count = splitwise_result['processed']
        skipped_not_involved = splitwise_result.get('skipped_not_involved', 0)  # ✅ NEW

        print(f"✅ Processed: {bank_count} bank, {splitwise_count} splitwise")
        if skipped_not_involved > 0:
            print(f"⏭️  Skipped: {skipped_not_involved} splitwise (not involved)")  # ✅ NEW

        update_session_counts(session_id, bank_count, splitwise_count, 0, skipped_not_involved)  # ✅ Updated
        
        # Step 5: Run analysis pipeline (linking, categorization)
        print("🧠 Running analysis pipeline...")
        run_full_pipeline(session_id)
        
        # Step 6: Mark as completed
        print(f"✅ Analysis complete for session: {session_id}")
        update_session_status(session_id, 'completed')
        
        # Optional: Clean up files
        # os.remove(bank_filepath)
        # os.remove(splitwise_filepath)
        
    except Exception as e:
        print(f"❌ Analysis failed for session {session_id}: {e}")
        import traceback
        traceback.print_exc()
        update_session_status(session_id, 'failed', str(e))


def update_session_status(session_id: str, status: str, error_message: str = None):
    """Update session status in database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    if error_message:
        # Store error in a way that doesn't break existing schema
        # For now, just update status
        cur.execute("""
            UPDATE upload_sessions
            SET status = %s
            WHERE id = %s
        """, (status, session_id))
    else:
        cur.execute("""
            UPDATE upload_sessions
            SET status = %s
            WHERE id = %s
        """, (status, session_id))
    
    conn.commit()
    cur.close()
    conn.close()


def start_analysis_thread(session_id: str, bank_filepath: str, splitwise_filepath: str,
                         start_date: str, end_date: str):
    """
    Start analysis in a background thread
    """
    thread = threading.Thread(
        target=run_analysis_pipeline,
        args=(session_id, bank_filepath, splitwise_filepath, start_date, end_date),
        daemon=True  # Thread dies when main program exits
    )
    thread.start()
    print(f"🔄 Analysis thread started for session: {session_id}")