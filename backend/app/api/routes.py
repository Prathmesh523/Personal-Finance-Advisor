
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from app.api.schemas import (
    SessionListResponse, SessionListItem,
    MetricsResponse, NetConsumption, ConsumptionBreakdown,
    CategoryResponse, CategoryItem,
    TransactionListResponse, Transaction,
    WarningsResponse,
    UploadResponse, SessionStatus,
    AvailableSessionsResponse, ComparisonResponse

)
from app.api.upload_handler import save_uploaded_file, start_analysis_thread  # NEW
from app.services.analytics import (
    get_monthly_metrics,
    get_category_breakdown,
    get_unlinked_splitwise_payer
)
from app.chatbot.intent_classifier import classify_intent
from app.chatbot.filter_extractor import extract_filters
from app.chatbot.query_builder import build_query
from app.chatbot.response_formatter import format_response
from app.database.connection import get_db_connection
from datetime import datetime
from typing import Optional
import math

router = APIRouter()


@router.get("/health")
def health_check():
    """Check if API is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "finance-advisor-api"
    }

@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    bank_file: UploadFile = File(..., description="Bank statement CSV"),
    splitwise_file: UploadFile = File(..., description="Splitwise export CSV"),
    month: int = Form(..., ge=1, le=12, description="Month (1-12)"),
    year: int = Form(..., ge=2020, le=2030, description="Year"),
    family_members: Optional[str] = Form(None, description="Comma-separated family names"),
    monthly_rent: Optional[float] = Form(None, description="Monthly rent amount")
):
    """
    Upload bank and splitwise CSV files for analysis
    """
    try:
        # Validate file types
        if not bank_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Bank file must be CSV")
        if not splitwise_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Splitwise file must be CSV")
        
        # Parse config
        config = {}
        if family_members:
            # Split by comma and clean whitespace
            config['family_members'] = [name.strip() for name in family_members.split(',') if name.strip()]
        if monthly_rent:
            config['monthly_rent'] = monthly_rent
        
        # Create upload session with config
        from app.services.session_manager import create_upload_session, check_duplicate_session
        
        month_str = f"{year}-{month:02d}"
        
        # Check for duplicates
        duplicate = check_duplicate_session(user_id=1, selected_month=month_str)
        if duplicate['exists']:
            raise HTTPException(
                status_code=409,
                detail=f"Month {month_str} already analyzed. Session ID: {duplicate['session_id']}"
            )
        
        # Create new session with config
        session_info = create_upload_session(
            user_id=1,
            selected_month=month,
            selected_year=year,
            config=config  # NEW
        )
        
        session_id = session_info['session_id']
        start_date = session_info['start_date']
        end_date = session_info['end_date']
        
        # Save uploaded files
        bank_filepath = save_uploaded_file(bank_file, session_id, 'bank')
        splitwise_filepath = save_uploaded_file(splitwise_file, session_id, 'splitwise')
        
        # Start analysis in background thread
        start_analysis_thread(session_id, bank_filepath, splitwise_filepath, start_date, end_date)
        
        return UploadResponse(
            session_id=session_id,
            status="processing",
            message="Analysis started. Check status endpoint for progress.",
            selected_month=month_str
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions():
    """
    Get list of all analysis sessions
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                id,
                selected_month,
                status,
                bank_count + splitwise_count as total_txns,
                created_at
            FROM upload_sessions
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        sessions = []
        for row in cur.fetchall():
            sessions.append(SessionListItem(
                id=row[0],
                month=row[1],
                status=row[2],
                transaction_count=row[3],
                created_at=row[4]
            ))
        
        cur.close()
        conn.close()
        
        return SessionListResponse(sessions=sessions)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/available", response_model=AvailableSessionsResponse)
def get_available_sessions():
    """
    Get list of all completed sessions for comparison
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                id,
                selected_month,
                status,
                bank_count + splitwise_count as total_txns,
                created_at
            FROM upload_sessions
            WHERE status = 'completed'
            ORDER BY selected_month DESC
        """)
        
        sessions = []
        for row in cur.fetchall():
            sessions.append({
                'session_id': row[0],
                'month': row[1],
                'status': row[2],
                'transaction_count': row[3],
                'created_at': row[4].isoformat()
            })
        
        cur.close()
        conn.close()
        
        return {'sessions': sessions, 'count': len(sessions)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/status", response_model=SessionStatus)
def get_session_status(session_id: str):
    """
    Check analysis status and progress
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get session info
        cur.execute("""
            SELECT 
                id,
                status,
                selected_month,
                bank_count,
                splitwise_count,
                created_at
            FROM upload_sessions
            WHERE id = %s
        """, (session_id,))
        
        result = cur.fetchone()
        if not result:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_id, status, month, bank_count, splitwise_count, created_at = result
        
        # Get processing progress from BOTH tables
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'LINKED' THEN 1 ELSE 0 END) as linked,
                SUM(CASE WHEN status = 'TRANSFER' THEN 1 ELSE 0 END) as transfers
            FROM bank_transactions
            WHERE upload_session_id = %s
        """, (session_id,))
        
        bank_result = cur.fetchone()
        bank_total, bank_linked, bank_transfers = bank_result if bank_result else (0, 0, 0)
        
        # Get splitwise linked count
        cur.execute("""
            SELECT COUNT(*) 
            FROM splitwise_transactions
            WHERE upload_session_id = %s AND status = 'LINKED'
        """, (session_id,))
        
        split_linked = cur.fetchone()[0] or 0
        
        cur.close()
        conn.close()
        
        return SessionStatus(
            session_id=session_id,
            status=status,
            selected_month=month,
            progress={
                "bank_processed": bank_count or 0,
                "splitwise_processed": splitwise_count or 0,
                "total_transactions": (bank_count or 0) + (splitwise_count or 0),
                "linked_pairs": (bank_linked or 0),  # Count from bank side only
                "settlements": bank_transfers or 0
            },
            created_at=created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/sessions/{session_id}/metrics", response_model=MetricsResponse)
def get_session_metrics(session_id: str):
    """
    Get financial metrics for a session
    """
    try:
        # Verify session exists
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM upload_sessions WHERE id = %s", (session_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Session not found")
        cur.close()
        conn.close()
        
        # Get metrics using existing service
        metrics = get_monthly_metrics(session_id)
        
        # Calculate difference
        difference = metrics['cash_outflow'] - metrics['net_consumption']['total']
        
        # Format response
        return MetricsResponse(
            session_id=session_id,
            net_consumption=NetConsumption(
                total=metrics['net_consumption']['total'],
                breakdown=ConsumptionBreakdown(**metrics['net_consumption']['breakdown'])
            ),
            cash_outflow=metrics['cash_outflow'],
            monthly_float=metrics['monthly_float'],
            difference=difference
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/categories", response_model=CategoryResponse)
def get_session_categories(session_id: str):
    """
    Get category breakdown for a session
    """
    try:
        # Verify session exists
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM upload_sessions WHERE id = %s", (session_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Session not found")
        cur.close()
        conn.close()
        
        # Get category breakdown using existing service
        categories_data = get_category_breakdown(session_id)
        
        # Calculate total
        total_spending = sum(cat['amount'] for cat in categories_data)
        
        # Format response
        categories = [
            CategoryItem(**cat) for cat in categories_data
        ]
        
        return CategoryResponse(
            categories=categories,
            total_spending=total_spending
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/transactions", response_model=TransactionListResponse)
def get_session_transactions(
    session_id: str,
    source: Optional[str] = Query(None, description="Filter by source (BANK or SPLITWISE)"),
    status: Optional[str] = Query(None, description="Filter by status (LINKED, UNLINKED, TRANSFER)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Get paginated list of transactions with filters
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verify session exists
        cur.execute("SELECT id FROM upload_sessions WHERE id = %s", (session_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Session not found")

        # Build query with filters
        where_clauses = []
        params = []
        
        # We need UNION of both tables
        if source == 'BANK' or source is None:
            bank_query = """
                SELECT 
                    id, date, description, amount, category, 
                    'BANK' as source, status, linked_splitwise_id as link_id, 
                    match_confidence, match_method
                FROM bank_transactions
                WHERE upload_session_id = %s AND user_id = %s
            """
            bank_params = [session_id, user_id]
            
            if status:
                bank_query += " AND status = %s"
                bank_params.append(status)
            
            if category:
                bank_query += " AND category = %s"
                bank_params.append(category)
        
        if source == 'SPLITWISE' or source is None:
            split_query = """
                SELECT 
                    id, date, description, 
                    CASE WHEN role = 'PAYER' THEN -total_cost ELSE -my_share END as amount,
                    category, 'SPLITWISE' as source, status, 
                    linked_bank_id as link_id, match_confidence, match_method
                FROM splitwise_transactions
                WHERE upload_session_id = %s AND user_id = %s
            """
            split_params = [session_id, user_id]
            
            if status:
                split_query += " AND status = %s"
                split_params.append(status)
            
            if category:
                split_query += " AND category = %s"
                split_params.append(category)
        
        # Combine queries
        if source == 'BANK':
            final_query = bank_query
            params = bank_params
        elif source == 'SPLITWISE':
            final_query = split_query
            params = split_params
        else:
            final_query = f"({bank_query}) UNION ALL ({split_query})"
            params = bank_params + split_params
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({final_query}) as combined"
        cur.execute(count_query, params)
        total = cur.fetchone()[0]
        
        # Calculate pagination
        offset = (page - 1) * limit
        total_pages = math.ceil(total / limit) if total > 0 else 1
        
        # Get paginated transactions
        paginated_query = f"""
            SELECT * FROM ({final_query}) as combined
            ORDER BY date DESC
            LIMIT %s OFFSET %s
        """
        cur.execute(paginated_query, params + [limit, offset])

        transactions = []
        for row in cur.fetchall():
            transactions.append(Transaction(
                id=row[0],
                date=row[1],
                description=row[2],
                amount=float(row[3]),
                category=row[4],
                source=row[5],
                status=row[6],
                link_id=row[7],
                match_confidence=float(row[8]) if row[8] else None,
                match_method=row[9]
            ))
        
        cur.close()
        conn.close()
        
        return TransactionListResponse(
            transactions=transactions,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/warnings", response_model=WarningsResponse)
def get_session_warnings(session_id: str):
    """
    Get warnings about potential double-counting
    """
    try:
        # Verify session exists
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM upload_sessions WHERE id = %s", (session_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Session not found")
        cur.close()
        conn.close()
        
        # Get unlinked payer transactions using existing service
        unlinked_data = get_unlinked_splitwise_payer(session_id)
        
        # No need to recalculate - already done in service ✅
        
        return WarningsResponse(
            unlinked_payer=unlinked_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
  

@router.get("/sessions/{session_id}/daily-spending")
def get_daily_spending(session_id: str):
    """
    Get spending aggregated by day
    Returns daily totals for chart visualization
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verify session exists
        cur.execute("SELECT id FROM upload_sessions WHERE id = %s", (session_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get daily spending (expenses only, exclude transfers)
        cur.execute("""
            SELECT 
                date,
                SUM(total_spent) as total_spent,
                SUM(transaction_count) as transaction_count
            FROM (
                SELECT 
                    date,
                    SUM(ABS(amount)) as total_spent,
                    COUNT(*) as transaction_count
                FROM bank_transactions
                WHERE upload_session_id = %s
                  AND amount < 0
                  AND status != 'TRANSFER'
                GROUP BY date
                
                UNION ALL
                
                SELECT 
                    date,
                    SUM(my_share) as total_spent,
                    COUNT(*) as transaction_count
                FROM splitwise_transactions
                WHERE upload_session_id = %s
                  AND role IN ('PAYER', 'BORROWER')
                GROUP BY date
            ) as combined
            GROUP BY date
            ORDER BY date ASC
        """, (session_id, session_id))
        
        daily_data = []
        for row in cur.fetchall():
            daily_data.append({
                'date': row[0].isoformat(),
                'amount': float(row[1]),
                'count': row[2]
            })
        
        cur.close()
        conn.close()
        
        return {
            'daily_spending': daily_data,
            'total_days': len(daily_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/transactions/grouped")
def get_grouped_transactions(
    session_id: str,
    source: Optional[str] = Query(None, description="Filter by source (BANK or SPLITWISE)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Get transactions grouped by date with 3 types:
    1. Independent Bank
    2. Independent Splitwise  
    3. Linked (merged)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verify session exists
        cur.execute("SELECT id FROM upload_sessions WHERE id = %s", (session_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Session not found")
        
        user_id = 1
        all_transactions = []
        
        # Build WHERE conditions for category filter
        category_filter = ""
        category_params = []
        if category:
            category_filter = " AND category = %s"
            category_params = [category]
        
        # TYPE 1: Independent Bank Transactions
        if source in [None, 'BANK']:
            cur.execute(f"""
                SELECT 
                    id, date, description, amount, category,
                    'BANK' as source, 'independent' as txn_type,
                    status, NULL as link_id, NULL as match_confidence, NULL as match_method,
                    NULL as bank_amount, NULL as my_share, NULL as split_percentage
                FROM bank_transactions
                WHERE upload_session_id = %s
                  AND user_id = %s
                  AND status = 'UNLINKED'
                  {category_filter}
                ORDER BY date DESC, id DESC
            """, [session_id, user_id] + category_params)
            
            all_transactions.extend(cur.fetchall())
        
        # TYPE 2: Independent Splitwise Transactions
        if source in [None, 'SPLITWISE']:
            cur.execute(f"""
                SELECT 
                    id, date, description, -my_share as amount, category,
                    'SPLITWISE' as source, 'independent' as txn_type,
                    status, NULL as link_id, NULL as match_confidence, NULL as match_method,
                    NULL as bank_amount, my_share, NULL as split_percentage,
                    role  -- ADD THIS
                FROM splitwise_transactions
                WHERE upload_session_id = %s
                AND user_id = %s
                AND status = 'UNLINKED'
                {category_filter}
                ORDER BY date DESC, id DESC
            """, [session_id, user_id] + category_params)
            
            all_transactions.extend(cur.fetchall())
        
        # TYPE 3: Linked Transactions (merged)
        if source in [None, 'BANK', 'SPLITWISE']:
            # Build category filter with table prefix
            linked_category_filter = ""
            if category:
                linked_category_filter = " AND b.category = %s"  # Specify b.category
            
            cur.execute(f"""
                SELECT 
                    b.id, b.date, s.description, b.amount, b.category,
                    'LINKED' as source, 'linked' as txn_type,
                    b.status, b.linked_splitwise_id as link_id, 
                    b.match_confidence, b.match_method,
                    b.amount as bank_amount, s.my_share,
                    ROUND((s.my_share / s.total_cost * 100)::numeric, 0) as split_percentage
                FROM bank_transactions b
                JOIN splitwise_transactions s ON b.linked_splitwise_id = s.id
                WHERE b.upload_session_id = %s
                AND b.user_id = %s
                AND b.status = 'LINKED'
                {linked_category_filter}
                ORDER BY b.date DESC, b.id DESC
            """, [session_id, user_id] + category_params)
            
            all_transactions.extend(cur.fetchall())
        
        # Sort all by date
        all_transactions.sort(key=lambda x: (x[1], x[0]), reverse=True)
        
        # Group by date
        from collections import defaultdict
        grouped = defaultdict(list)
        
        for row in all_transactions:
            date_str = row[1].isoformat()
            
            txn_obj = {
                'id': row[0],
                'date': date_str,
                'description': row[2],
                'amount': float(row[3]),
                'category': row[4],
                'source': row[5],
                'txn_type': row[6],
                'status': row[7],
                'link_id': row[8],
                'match_confidence': float(row[9]) if row[9] else None,
                'match_method': row[10],
                'bank_amount': float(row[11]) if row[11] else None,
                'my_share': float(row[12]) if row[12] else None,
                'split_percentage': int(row[13]) if row[13] else None,
                'role': row[14] if len(row) > 14 else None
            }
            
            grouped[date_str].append(txn_obj)
        
        # Convert to list of groups
        groups = []
        for date_str, transactions in grouped.items():
            total_amount = sum(t['amount'] for t in transactions)
            groups.append({
                'date': date_str,
                'transactions': transactions,
                'total_amount': total_amount,
                'count': len(transactions)
            })
        
        # Sort by date descending
        groups.sort(key=lambda x: x['date'], reverse=True)
        
        # Pagination
        total_groups = len(groups)
        total_pages = math.ceil(total_groups / limit) if total_groups > 0 else 1
        offset = (page - 1) * limit
        paginated_groups = groups[offset:offset + limit]
        
        cur.close()
        conn.close()
        
        return {
            'groups': paginated_groups,
            'total': total_groups,
            'page': page,
            'limit': limit,
            'total_pages': total_pages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/compare", response_model=ComparisonResponse)
def compare_sessions(
    session1: str = Query(..., description="First session ID"),
    session2: str = Query(..., description="Second session ID")
):
    """
    Compare two analysis sessions
    """
    try:
        # Validate: sessions exist and are different
        if session1 == session2:
            raise HTTPException(status_code=400, detail="Cannot compare same session")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verify both sessions exist and get months
        cur.execute("""
            SELECT id, selected_month 
            FROM upload_sessions 
            WHERE id IN (%s, %s)
        """, (session1, session2))
        
        results = cur.fetchall()
        if len(results) != 2:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="One or both sessions not found")
        
        session_months = {row[0]: row[1] for row in results}
        
        # Get metrics for both sessions
        from app.services.analytics import get_monthly_metrics
        
        metrics1 = get_monthly_metrics(session1)
        metrics2 = get_monthly_metrics(session2)
        
        # Calculate metric comparisons
        def calc_comparison(val1, val2):
            diff = val2 - val1
            pct = (diff / val1 * 100) if val1 != 0 else (100 if val2 > 0 else 0)
            return {
                'session1_value': val1,
                'session2_value': val2,
                'difference': diff,
                'percentage_change': round(pct, 1)
            }
        
        net_consumption_comp = calc_comparison(
            metrics1['net_consumption']['total'],
            metrics2['net_consumption']['total']
        )
        
        cash_outflow_comp = calc_comparison(
            metrics1['cash_outflow'],
            metrics2['cash_outflow']
        )
        
        float_comp = calc_comparison(
            metrics1['monthly_float'],
            metrics2['monthly_float']
        )
        
        # Category comparison
        cats1 = {cat['category']: cat['amount'] for cat in metrics1['category_breakdown']}
        cats2 = {cat['category']: cat['amount'] for cat in metrics2['category_breakdown']}
        
        all_categories = set(cats1.keys()) | set(cats2.keys())
        
        category_comparison = []
        for cat in all_categories:
            amt1 = cats1.get(cat, 0)
            amt2 = cats2.get(cat, 0)
            diff = amt2 - amt1
            pct = (diff / amt1 * 100) if amt1 != 0 else (100 if amt2 > 0 else 0)
            
            category_comparison.append({
                'category': cat,
                'session1_amount': amt1,
                'session2_amount': amt2,
                'difference': diff,
                'percentage_change': round(pct, 1)
            })
        
        # Sort by absolute difference
        category_comparison.sort(key=lambda x: abs(x['difference']), reverse=True)
        
        # Top increases and decreases
        increases = [c for c in category_comparison if c['difference'] > 0]
        decreases = [c for c in category_comparison if c['difference'] < 0]
        
        increases.sort(key=lambda x: x['difference'], reverse=True)
        decreases.sort(key=lambda x: x['difference'])
        
        # Daily averages - count distinct days from bank transactions
        cur.execute("""
            SELECT COUNT(DISTINCT date)
            FROM bank_transactions
            WHERE upload_session_id = %s
            AND amount < 0
            AND status != 'TRANSFER'
        """, (session1,))
        days1 = cur.fetchone()[0] or 1

        cur.execute("""
            SELECT COUNT(DISTINCT date)
            FROM bank_transactions
            WHERE upload_session_id = %s
            AND amount < 0
            AND status != 'TRANSFER'
        """, (session2,))
        days2 = cur.fetchone()[0] or 1
        
        daily_avg1 = metrics1['net_consumption']['total'] / days1
        daily_avg2 = metrics2['net_consumption']['total'] / days2
        
        cur.close()
        conn.close()
        
        return {
            'session1_id': session1,
            'session1_month': session_months[session1],
            'session2_id': session2,
            'session2_month': session_months[session2],
            'net_consumption': net_consumption_comp,
            'cash_outflow': cash_outflow_comp,
            'monthly_float': float_comp,
            'category_comparison': category_comparison,
            'session1_daily_avg': round(daily_avg1, 2),
            'session2_daily_avg': round(daily_avg2, 2),
            'top_increases': increases[:5],
            'top_decreases': decreases[:5]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/sessions/{session_id}/unmatched-splitwise")
def get_unmatched_splitwise_transactions(session_id: str):
    """
    Get all unmatched splitwise PAYER transactions with suggested bank matches
    """
    try:
        from app.services.manual_linking import get_unmatched_splitwise
        
        # Verify session exists
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM upload_sessions WHERE id = %s", (session_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Session not found")
        cur.close()
        conn.close()
        
        unmatched = get_unmatched_splitwise(session_id)
        
        return {
            'unmatched': unmatched,
            'count': len(unmatched)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/link-transactions")
def link_transactions_manually(
    session_id: str,
    splitwise_id: int = Query(..., description="Splitwise transaction ID"),
    bank_id: int = Query(..., description="Bank transaction ID")
):
    """
    Manually link a splitwise transaction to a bank transaction
    """
    try:
        from app.services.manual_linking import link_transactions_manual
        
        link_transactions_manual(splitwise_id, bank_id, session_id)
        
        return {
            'success': True,
            'message': 'Transactions linked successfully'
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/skip-transaction")
def skip_splitwise_transaction(
    session_id: str,
    splitwise_id: int = Query(..., description="Splitwise transaction ID"),
    reason: str = Query('no_match', description="Reason for skipping")
):
    """
    Mark splitwise transaction as skipped (no bank match exists)
    """
    try:
        from app.services.manual_linking import skip_transaction
        
        skip_transaction(splitwise_id, reason, session_id)
        
        return {
            'success': True,
            'message': 'Transaction marked as skipped'
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
def get_available_categories():
    """
    Get list of available categories
    """
    categories = [
        'Food & Dining',
        'Groceries',
        'Transport',
        'Shopping',
        'Entertainment',
        'Bills & Utilities',
        'Health',
        'Investment',
        'Education',
        'Family Transfer',
        'Rent',
        'Settlement',
        'Other'
    ]
    
    return {'categories': categories}


@router.get("/sessions/{session_id}/transactions/{transaction_id}/similar-count")
def get_similar_transaction_count(
    session_id: str,
    transaction_id: int,
    source: str = Query(..., description="BANK or SPLITWISE")
):
    """
    Count similar transactions for preview
    """
    try:
        from app.services.categorization_rules import extract_merchant_pattern, count_similar_transactions
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get transaction description
        if source == 'BANK':
            cur.execute("""
                SELECT description FROM bank_transactions
                WHERE id = %s AND upload_session_id = %s
            """, (transaction_id, session_id))
        else:
            cur.execute("""
                SELECT description FROM splitwise_transactions
                WHERE id = %s AND upload_session_id = %s
            """, (transaction_id, session_id))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if not result:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        description = result[0]
        pattern = extract_merchant_pattern(description)
        
        if not pattern:
            return {
                'pattern': None,
                'count': 0,
                'message': 'No pattern detected'
            }
        
        count = count_similar_transactions(session_id, source, pattern, transaction_id)
        
        return {
            'pattern': pattern,
            'count': count,
            'message': f'Found {count} similar transaction(s)'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/sessions/{session_id}/transactions/{transaction_id}/category")
def update_transaction_category(
    session_id: str,
    transaction_id: int,
    source: str = Query(..., description="BANK or SPLITWISE"),
    new_category: str = Query(..., description="New category name"),
    create_rule: bool = Query(False, description="Save as rule for future"),
    apply_to_similar: bool = Query(False, description="Apply to similar transactions")
):
    """
    Update transaction category with optional rule creation
    """
    try:
        from app.services.categorization_rules import (
            extract_merchant_pattern,
            save_categorization_rule,
            apply_rule_to_similar
        )
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get transaction description
        if source == 'BANK':
            cur.execute("""
                SELECT description FROM bank_transactions
                WHERE id = %s AND upload_session_id = %s
            """, (transaction_id, session_id))
        else:
            cur.execute("""
                SELECT description FROM splitwise_transactions
                WHERE id = %s AND upload_session_id = %s
            """, (transaction_id, session_id))
        
        result = cur.fetchone()
        if not result:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        description = result[0]
        
        # Update current transaction
        if source == 'BANK':
            cur.execute("""
                UPDATE bank_transactions
                SET category = %s
                WHERE id = %s
            """, (new_category, transaction_id))
        else:
            cur.execute("""
                UPDATE splitwise_transactions
                SET category = %s
                WHERE id = %s
            """, (new_category, transaction_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        updated_count = 1
        pattern = None
        
        # Apply to similar transactions if requested
        if apply_to_similar:
            pattern = extract_merchant_pattern(description)
            if pattern:
                similar_count = apply_rule_to_similar(
                    session_id, source, pattern, new_category, transaction_id
                )
                updated_count += similar_count
        
        # Save rule for future if requested
        if create_rule and pattern:
            save_categorization_rule(
                user_id=1,
                pattern=pattern,
                category=new_category,
                match_type='contains',
                source=source
            )
        
        return {
            'success': True,
            'message': f'Updated {updated_count} transaction(s)',
            'updated_count': updated_count,
            'pattern': pattern,
            'rule_saved': create_rule and pattern is not None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categorization-rules")
def get_categorization_rules(user_id: int = Query(1, description="User ID")):
    """
    Get all saved categorization rules
    """
    try:
        from app.services.categorization_rules import get_user_rules
        
        rules = get_user_rules(user_id)
        
        return {
            'rules': rules,
            'count': len(rules)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/recommendations")
def get_recommendations(session_id: str, user_id: int = Query(1)):
    """
    Get personalized recommendations for a session
    """
    try:
        from app.services.recommendations import get_all_recommendations
        
        # Verify session exists
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM upload_sessions WHERE id = %s", (session_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Session not found")
        cur.close()
        conn.close()
        
        recommendations = get_all_recommendations(session_id, user_id)
        
        return recommendations
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/chat")
def chat_query(
    question: str = Query(..., description="User's question"),
    user_id: int = Query(1, description="User ID")
):
    """
    Natural language chat interface
    NO session_id required - queries all data unless month specified
    """
    try:
        
        # Step 1: Classify intent
        intent = classify_intent(question)
        
        # Step 2: Extract filters (no session_id needed)
        filters = extract_filters(question, user_id)
        
        # Step 3: Build SQL query
        query_info = build_query(intent, filters)
        
        # Step 4: Execute query
        conn = get_db_connection()
        cur = conn.cursor()
        
        if query_info:
            cur.execute(query_info['sql'], query_info['params'])
            rows = cur.fetchall()
            
            data = []
            for row in rows:
                row_dict = {col: row[i] for i, col in enumerate(query_info['columns'])}
                data.append(row_dict)
            
            query_info['data'] = data
        else:
            query_info = None
        
        cur.close()
        conn.close()
        
        # Step 5: Format response
        response = format_response(intent, query_info, filters, question)
        
        return {
            'question': question,
            'intent': intent,
            'filters': filters,
            'answer': response['answer'],
            'data': response['data'],
            'show_table': response['show_table']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    