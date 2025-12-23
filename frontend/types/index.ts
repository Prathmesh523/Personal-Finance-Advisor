// types/index.ts

// Session related
export interface Session {
  id: string;
  month: string;
  status: 'processing' | 'completed' | 'failed';
  transaction_count: number;
  created_at: string;
}

export interface SessionStatus {
  session_id: string;
  status: 'processing' | 'completed' | 'failed';
  selected_month: string;
  progress: {
    bank_processed: number;
    splitwise_processed: number;
    total_transactions: number;
    linked_pairs: number;
    settlements: number;
  };
  created_at: string;
  error_message?: string;
}

// Metrics related
export interface ConsumptionBreakdown {
  solo_spend: number;
  split_i_paid: number;
  split_they_paid: number;
}

export interface NetConsumption {
  total: number;
  breakdown: ConsumptionBreakdown;
}

export interface Metrics {
  session_id: string;
  net_consumption: NetConsumption;
  cash_outflow: number;
  monthly_float: number;
  difference: number;
}

// Category related
export interface CategoryItem {
  category: string;
  amount: number;
  percentage: number;
  count?: number;
}

export interface CategoryBreakdown {
  categories: CategoryItem[];
  total_spending: number;
}

// Transaction related
export interface Transaction {
  id: number;
  date: string;
  description: string;
  amount: number;
  category: string | null;
  source: string;
  txn_type: 'independent' | 'linked';
  status: string;
  link_id?: number | null;
  match_confidence?: number | null;
  match_method?: string | null;
  bank_amount?: number | null;
  my_share?: number | null;
  split_percentage?: number | null;
  role?: string | null;  // ADD THIS
}

export interface TransactionList {
  transactions: Transaction[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

// Upload related
export interface UploadResponse {
  session_id: string;
  status: string;
  message: string;
  selected_month: string;
}

// Warnings related
export interface UnlinkedTransaction {
  date: string;
  description: string;
  total_bill: number;
  owed_to_you: number;
  your_share: number;
  category: string | null;
}

export interface Warnings {
  unlinked_payer: {
    count: number;
    total_amount: number;
    transactions: UnlinkedTransaction[];
  };
}

// Daily spending
export interface DailySpendingItem {
  date: string;
  amount: number;
  count: number;
}

export interface DailySpendingResponse {
  daily_spending: DailySpendingItem[];
  total_days: number;
}

// Grouped transactions
export interface TransactionGroup {
  date: string;
  transactions: Transaction[];
  total_amount: number;
  count: number;
}

export interface GroupedTransactionsResponse {
  groups: TransactionGroup[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

// Comparison types
export interface AvailableSession {
  session_id: string;
  month: string;
  status: string;
  transaction_count: number;
  created_at: string;
}

export interface AvailableSessionsResponse {
  sessions: AvailableSession[];
  count: number;
}

export interface MetricComparison {
  session1_value: number;
  session2_value: number;
  difference: number;
  percentage_change: number;
}

export interface CategoryComparison {
  category: string;
  session1_amount: number;
  session2_amount: number;
  difference: number;
  percentage_change: number;
}

export interface ComparisonResponse {
  session1_id: string;
  session1_month: string;
  session2_id: string;
  session2_month: string;
  net_consumption: MetricComparison;
  cash_outflow: MetricComparison;
  monthly_float: MetricComparison;
  category_comparison: CategoryComparison[];
  session1_daily_avg: number;
  session2_daily_avg: number;
  top_increases: CategoryComparison[];
  top_decreases: CategoryComparison[];
}

export interface SuggestedMatch {
  id: number;
  date: string;
  description: string;
  amount: number;
  category: string | null;
  match_score: number;
  match_reason: string;
}

export interface UnmatchedSplitwise {
  id: number;
  date: string;
  description: string;
  total_cost: number;
  my_share: number;
  category: string | null;
  suggested_matches: SuggestedMatch[];
  preselect_id: number | null;
}

export interface UnmatchedResponse {
  unmatched: UnmatchedSplitwise[];
  count: number;
}

export interface CategoryRule {
  id: number;
  pattern: string;
  category: string;
  match_type: string;
  source: string;
  created_at: string;
}

export interface SimilarCountResponse {
  pattern: string | null;
  count: number;
  message: string;
}

export interface UpdateCategoryResponse {
  success: boolean;
  message: string;
  updated_count: number;
  pattern: string | null;
  rule_saved: boolean;
}