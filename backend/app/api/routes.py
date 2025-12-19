
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from app.api.schemas import (
    SessionListResponse, SessionListItem,
    MetricsResponse, NetConsumption, ConsumptionBreakdown,
    CategoryResponse, CategoryItem,
    TransactionListResponse, Transaction,
    WarningsResponse,
    UploadResponse, SessionStatus  # NEW
)
from app.api.upload_handler import save_uploaded_file, start_analysis_thread  # NEW
from app.services.analytics import (
    get_monthly_metrics,
    get_category_breakdown,
    get_unlinked_splitwise_payer
)
from app.database.connection import get_db_connection
from datetime import datetime
from typing import Optional
import math

router = APIRouter()

# ============================================================================
# EXISTING ENDPOINTS
# ============================================================================

@router.get("/health")
def health_check():
    """Check if API is running"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "finance-advisor-api"
    }

@router.get("/test-db")
def test_database():
    """Test database connection"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM transactions")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        return {
            "status": "connected",
            "total_transactions": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# ============================================================================
# NEW ENDPOINTS
# ============================================================================

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
        where_clauses = ["upload_session_id = %s"]
        params = [session_id]
        
        if source:
            where_clauses.append("source = %s")
            params.append(source)
        
        if status:
            where_clauses.append("status = %s")
            params.append(status)
        
        if category:
            where_clauses.append("category = %s")
            params.append(category)
        
        where_clause = " AND ".join(where_clauses)
        
        # Get total count
        cur.execute(f"""
            SELECT COUNT(*) 
            FROM transactions 
            WHERE {where_clause}
        """, params)
        total = cur.fetchone()[0]
        
        # Calculate pagination
        offset = (page - 1) * limit
        total_pages = math.ceil(total / limit) if total > 0 else 1
        
        # Get paginated transactions
        cur.execute(f"""
            SELECT 
                id, date, description, amount, category, 
                source, status, link_id, match_confidence, match_method
            FROM transactions
            WHERE {where_clause}
            ORDER BY date DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])
        
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
    
# ============================================================================
# UPLOAD ENDPOINT
# ============================================================================

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

# ============================================================================
# STATUS ENDPOINT
# ============================================================================

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
        
        # Get processing progress
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'LINKED' THEN 1 ELSE 0 END) as linked,
                SUM(CASE WHEN status = 'TRANSFER' THEN 1 ELSE 0 END) as transfers
            FROM transactions
            WHERE upload_session_id = %s
        """, (session_id,))
        
        progress_result = cur.fetchone()
        total, linked, transfers = progress_result if progress_result else (0, 0, 0)
        
        cur.close()
        conn.close()
        
        return SessionStatus(
            session_id=session_id,
            status=status,
            selected_month=month,
            progress={
                "bank_processed": bank_count or 0,
                "splitwise_processed": splitwise_count or 0,
                "total_transactions": total,
                "linked_pairs": (linked or 0) // 2,
                "settlements": transfers or 0
            },
            created_at=created_at
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
                SUM(ABS(amount)) as total_spent,
                COUNT(*) as transaction_count
            FROM transactions
            WHERE upload_session_id = %s
              AND amount < 0
              AND status != 'TRANSFER'
            GROUP BY date
            ORDER BY date ASC
        """, (session_id,))
        
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
    status: Optional[str] = Query(None, description="Filter by status (LINKED, UNLINKED, TRANSFER)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Get transactions grouped by date
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
        where_clauses = ["upload_session_id = %s"]
        params = [session_id]
        
        if source:
            where_clauses.append("source = %s")
            params.append(source)
        
        if status:
            where_clauses.append("status = %s")
            params.append(status)
        
        if category:
            where_clauses.append("category = %s")
            params.append(category)
        
        where_clause = " AND ".join(where_clauses)
        
        # Get all transactions for grouping
        cur.execute(f"""
            SELECT 
                id, date, description, amount, category, 
                source, status, link_id, match_confidence, match_method
            FROM transactions
            WHERE {where_clause}
            ORDER BY date DESC, id DESC
        """, params)
        
        all_transactions = cur.fetchall()
        
        # Group by date
        from collections import defaultdict
        grouped = defaultdict(list)
        
        for row in all_transactions:
            date_str = row[1].isoformat()
            grouped[date_str].append({
                'id': row[0],
                'date': date_str,
                'description': row[2],
                'amount': float(row[3]),
                'category': row[4],
                'source': row[5],
                'status': row[6],
                'link_id': row[7],
                'match_confidence': float(row[8]) if row[8] else None,
                'match_method': row[9]
            })
        
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