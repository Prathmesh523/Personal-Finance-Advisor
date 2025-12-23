// app/transactions/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useSession } from '@/lib/session-context';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { formatMonth } from '@/lib/utils';
import { TransactionGroup } from '@/types';
import { GroupedTransactionList } from '@/components/GroupedTransactionList';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Calendar } from 'lucide-react';

export default function TransactionsPage() {
  const router = useRouter();
  const { currentSession, currentSessionMonth } = useSession();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [groups, setGroups] = useState<TransactionGroup[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Filters
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  // Available categories
  const [categories, setCategories] = useState<string[]>([]);

  useEffect(() => {
    // Wait for session
    if (!currentSession) return;

    // Read URL params and set filters FIRST
    const searchParams = new URLSearchParams(window.location.search);
    const categoryParam = searchParams.get('category');
    
    if (categoryParam && categoryParam !== categoryFilter) {
      setCategoryFilter(categoryParam);
      return; // Exit - let the state update trigger re-fetch
    }

    // Now fetch with current filters
    fetchTransactions(currentSession, currentPage);
  }, [currentSession, currentPage, sourceFilter, categoryFilter]);

  const fetchTransactions = async (sessionId: string, page: number) => {
    try {
      setLoading(true);
      setError(null);

      const params: any = { page, limit: 10 };

      if (sourceFilter !== 'all') params.source = sourceFilter;
      if (categoryFilter !== 'all') params.category = categoryFilter;

      const data = await api.getGroupedTransactions(sessionId, params);

      setGroups(data.groups);
      setTotalPages(data.total_pages);
      setTotalCount(data.total);

      // Extract unique categories from all transactions
      const allCategories = new Set<string>();
      data.groups.forEach((group) => {
        group.transactions.forEach((txn) => {
          if (txn.category) allCategories.add(txn.category);
        });
      });
      setCategories(Array.from(allCategories));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load transactions');
      console.error('Transactions error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    if (currentSession) {
      fetchTransactions(currentSession, currentPage);
    }
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleFilterChange = () => {
    setCurrentPage(1);
  };

  const resetFilters = () => {
    setSourceFilter('all');
    setCategoryFilter('all');
    setCurrentPage(1);
  };

  if (loading && groups.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading transactions...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="text-red-600">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600 mb-4">{error}</p>
            <Button onClick={() => router.push('/dashboard')}>
              Back to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const hasActiveFilters = sourceFilter !== 'all' || categoryFilter !== 'all';

  // Count total transactions across all groups
  const totalTransactions = groups.reduce((sum, group) => sum + group.count, 0);

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Transactions</h1>
              <p className="text-gray-600 mt-2">
                {totalCount} group{totalCount !== 1 ? 's' : ''} • {totalTransactions} transaction{totalTransactions !== 1 ? 's' : ''}
              </p>
            </div>
            {currentSessionMonth && (
              <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-lg">
                <Calendar className="w-5 h-5 text-blue-600" />
                <div>
                  <p className="text-xs text-gray-600">Analysis Period</p>
                  <p className="text-sm font-semibold text-gray-900">
                    {formatMonth(currentSessionMonth)}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Source Filter */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Source</label>
              <Select
                value={sourceFilter}
                onValueChange={(val) => {
                  setSourceFilter(val);
                  handleFilterChange();
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="BANK">Bank</SelectItem>
                  <SelectItem value="SPLITWISE">Splitwise</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Category Filter */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Category</label>
              <Select
                value={categoryFilter}
                onValueChange={(val) => {
                  setCategoryFilter(val);
                  handleFilterChange();
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  {categories.map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {cat}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Reset Button */}
            <div className="space-y-2">
              <label className="text-sm font-medium invisible">Action</label>
              <Button
                variant="outline"
                onClick={resetFilters}
                disabled={!hasActiveFilters}
                className="w-full"
              >
                Reset Filters
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

        {/* Grouped Transactions */}
        <GroupedTransactionList
          groups={groups}
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
          onRefresh={handleRefresh}
        />
      </div>
    </div>
  );
}