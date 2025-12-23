// lib/api.ts

import {
  Session,
  SessionStatus,
  Metrics,
  CategoryBreakdown,
  TransactionList,
  UploadResponse,
  Warnings,
  DailySpendingResponse,
  GroupedTransactionsResponse,
  AvailableSessionsResponse,
  ComparisonResponse,
  UnmatchedResponse,
  SimilarCountResponse,
  UpdateCategoryResponse,
  CategoryRule
} from '@/types';

const API_BASE_URL = 'http://localhost:8000/api/v1';

// Helper function for fetch
async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

// API Functions
export const api = {
  // Health check
  healthCheck: () => fetchAPI<{ status: string }>('/health'),

  // Sessions
  listSessions: () => fetchAPI<{ sessions: Session[] }>('/sessions'),

  getSessionStatus: (sessionId: string) =>
    fetchAPI<SessionStatus>(`/sessions/${sessionId}/status`),

  getMetrics: (sessionId: string) => fetchAPI<Metrics>(`/sessions/${sessionId}/metrics`),

  getCategoryBreakdown: (sessionId: string) => 
    fetchAPI<CategoryBreakdown>(`/sessions/${sessionId}/categories`),

  getWarnings: (sessionId: string) => fetchAPI<Warnings>(`/sessions/${sessionId}/warnings`),

  // Transactions
  getTransactions: (
    sessionId: string,
    params?: {
      source?: 'BANK' | 'SPLITWISE';
      status?: 'LINKED' | 'UNLINKED' | 'TRANSFER';
      category?: string;
      page?: number;
      limit?: number;
    }
  ) => {
    const queryParams = new URLSearchParams();
    if (params?.source) queryParams.append('source', params.source);
    if (params?.status) queryParams.append('status', params.status);
    if (params?.category) queryParams.append('category', params.category);
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());

    const query = queryParams.toString();
    return fetchAPI<TransactionList>(
      `/sessions/${sessionId}/transactions${query ? `?${query}` : ''}`
    );
  },

  // Upload
  uploadFiles: async (
    bankFile: File,
    splitwiseFile: File,
    month: number,
    year: number
  ): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('bank_file', bankFile);
    formData.append('splitwise_file', splitwiseFile);
    formData.append('month', month.toString());
    formData.append('year', year.toString());

    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || `Upload Error: ${response.status}`);
    }

    return response.json();
  },

  // Daily spending
  getDailySpending: (sessionId: string) =>
    fetchAPI<DailySpendingResponse>(`/sessions/${sessionId}/daily-spending`),

  // Grouped transactions
  getGroupedTransactions: (
    sessionId: string,
    params?: {
      source?: 'BANK' | 'SPLITWISE';
      status?: 'LINKED' | 'UNLINKED' | 'TRANSFER';
      category?: string;
      page?: number;
      limit?: number;
    }
  ) => {
    const queryParams = new URLSearchParams();
    if (params?.source) queryParams.append('source', params.source);
    if (params?.status) queryParams.append('status', params.status);
    if (params?.category) queryParams.append('category', params.category);
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());

    const query = queryParams.toString();
    return fetchAPI<GroupedTransactionsResponse>(
      `/sessions/${sessionId}/transactions/grouped${query ? `?${query}` : ''}`
    );
  },

  // Comparison
  getAvailableSessions: () =>
    fetchAPI<AvailableSessionsResponse>('/sessions/available'),

  compareSessions: (session1: string, session2: string) =>
    fetchAPI<ComparisonResponse>(`/compare?session1=${session1}&session2=${session2}`),

  // Manual Linking
  getUnmatchedSplitwise: (sessionId: string) =>
    fetchAPI<UnmatchedResponse>(`/sessions/${sessionId}/unmatched-splitwise`),

  linkTransactionsManually: (sessionId: string, splitwiseId: number, bankId: number) =>
    fetchAPI<{ success: boolean; message: string }>(
      `/sessions/${sessionId}/link-transactions?splitwise_id=${splitwiseId}&bank_id=${bankId}`,
      { method: 'POST' }
    ),

  skipTransaction: (sessionId: string, splitwiseId: number, reason: string = 'no_match') =>
    fetchAPI<{ success: boolean; message: string }>(
      `/sessions/${sessionId}/skip-transaction?splitwise_id=${splitwiseId}&reason=${reason}`,
      { method: 'POST' }
    ),

  // Categorization
  getCategories: () => fetchAPI<{ categories: string[] }>('/categories'),

  getSimilarCount: (sessionId: string, transactionId: number, source: string) =>
    fetchAPI<SimilarCountResponse>(
      `/sessions/${sessionId}/transactions/${transactionId}/similar-count?source=${source}`
    ),

  updateTransactionCategory: (
    sessionId: string,
    transactionId: number,
    source: string,
    newCategory: string,
    applyToSimilar: boolean,
    createRule: boolean
  ) =>
    fetchAPI<UpdateCategoryResponse>(
      `/sessions/${sessionId}/transactions/${transactionId}/category?source=${source}&new_category=${encodeURIComponent(
        newCategory
      )}&apply_to_similar=${applyToSimilar}&create_rule=${createRule}`,
      { method: 'PATCH' }
    ),

  getCategorizationRules: () =>  // ✅ NO SPACE
  fetchAPI<{ rules: CategoryRule[]; count: number }>('/categorization-rules'),
};