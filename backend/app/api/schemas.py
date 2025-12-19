from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, date

# ============================================================================
# SESSION SCHEMAS
# ============================================================================

class SessionListItem(BaseModel):
    id: str
    month: str
    status: str
    transaction_count: int
    created_at: datetime

class SessionListResponse(BaseModel):
    sessions: List[SessionListItem]

# ============================================================================
# METRICS SCHEMAS
# ============================================================================

class ConsumptionBreakdown(BaseModel):
    solo: float
    split_you_paid: float
    split_friend_paid: float

class NetConsumption(BaseModel):
    total: float
    breakdown: ConsumptionBreakdown

class MetricsResponse(BaseModel):
    session_id: str
    net_consumption: NetConsumption
    cash_outflow: float
    monthly_float: float
    difference: float

# ============================================================================
# CATEGORY SCHEMAS
# ============================================================================

class CategoryItem(BaseModel):
    category: str
    amount: float
    percentage: float
    count: Optional[int] = None

class CategoryResponse(BaseModel):
    categories: List[CategoryItem]
    total_spending: float

# ============================================================================
# TRANSACTION SCHEMAS
# ============================================================================

class Transaction(BaseModel):
    id: int
    date: date
    description: str
    amount: float
    category: Optional[str]
    source: str
    status: str
    link_id: Optional[int] = None
    match_confidence: Optional[float] = None
    match_method: Optional[str] = None

class TransactionListResponse(BaseModel):
    transactions: List[Transaction]
    total: int
    page: int
    limit: int
    total_pages: int

# ============================================================================
# WARNING SCHEMAS
# ============================================================================

class UnlinkedTransaction(BaseModel):
    date: date
    description: str
    total_bill: float
    owed_to_you: float
    your_share: float
    category: Optional[str]

class WarningsResponse(BaseModel):
    unlinked_payer: Dict

# ============================================================================
# UPLOAD SCHEMAS
# ============================================================================

class UploadResponse(BaseModel):
    session_id: str
    status: str
    message: str
    selected_month: str

class SessionStatus(BaseModel):
    session_id: str
    status: str  # 'processing', 'completed', 'failed'
    selected_month: str
    progress: Dict
    created_at: datetime
    error_message: Optional[str] = None

# ============================================================================
# DAILY SPENDING SCHEMAS
# ============================================================================

class DailySpendingItem(BaseModel):
    date: str
    amount: float
    count: int

class DailySpendingResponse(BaseModel):
    daily_spending: List[DailySpendingItem]
    total_days: int


# ============================================================================
# GROUPED TRANSACTIONS SCHEMAS
# ============================================================================

class TransactionGroup(BaseModel):
    date: str
    transactions: List[Transaction]
    total_amount: float
    count: int

class GroupedTransactionsResponse(BaseModel):
    groups: List[TransactionGroup]
    total: int
    page: int
    limit: int
    total_pages: int

# Add this to existing schemas

class UploadConfig(BaseModel):
    family_members: Optional[List[str]] = []
    monthly_rent: Optional[float] = None

# Update UploadResponse to include config
class UploadResponseWithConfig(BaseModel):
    session_id: str
    status: str
    message: str
    selected_month: str
    config: Optional[UploadConfig] = None
    
# ============================================================================
# COMPARISON SCHEMAS
# ============================================================================

class AvailableSession(BaseModel):
    session_id: str
    month: str
    status: str
    transaction_count: int
    created_at: str

class AvailableSessionsResponse(BaseModel):
    sessions: List[AvailableSession]
    count: int

class MetricComparison(BaseModel):
    session1_value: float
    session2_value: float
    difference: float
    percentage_change: float

class CategoryComparison(BaseModel):
    category: str
    session1_amount: float
    session2_amount: float
    difference: float
    percentage_change: float

class ComparisonResponse(BaseModel):
    session1_id: str
    session1_month: str
    session2_id: str
    session2_month: str
    
    net_consumption: MetricComparison
    cash_outflow: MetricComparison
    monthly_float: MetricComparison
    
    category_comparison: List[CategoryComparison]
    
    session1_daily_avg: float
    session2_daily_avg: float
    
    top_increases: List[CategoryComparison]
    top_decreases: List[CategoryComparison]