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
  solo: number;
  split_you_paid: number;
  split_friend_paid: number;
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
  source: 'BANK' | 'SPLITWISE';
  status: 'LINKED' | 'UNLINKED' | 'TRANSFER';
  link_id?: number;
  match_confidence?: number;
  match_method?: string;
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