// app/dashboard/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@/lib/session-context';
import { api } from '@/lib/api';
import { storage } from '@/lib/storage';
import { formatMonth } from '@/lib/utils';
import { Metrics, CategoryBreakdown, Warnings, DailySpendingResponse } from '@/types';
import { MetricCard } from '@/components/MetricCard';
import { CategoryChart } from '@/components/CategoryChart';
import { DailySpendingChart } from '@/components/DailySpendingChart';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Calendar } from 'lucide-react';

export default function DashboardPage() {
  const router = useRouter();
  const { currentSession, currentSessionMonth, loading: sessionLoading } = useSession();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [sessionMonth, setSessionMonth] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [categories, setCategories] = useState<CategoryBreakdown | null>(null);
  const [warnings, setWarnings] = useState<Warnings | null>(null);
  const [dailySpending, setDailySpending] = useState<DailySpendingResponse | null>(null);

  useEffect(() => {
    if (!currentSession) return;  // NEW: Wait for session
    
    fetchDashboardData(currentSession);  // NEW: Use from context
  }, [currentSession]);

  const fetchDashboardData = async (sessionId: string) => {
    try {
      setLoading(true);
      setError(null);

      const [metricsData, categoriesData, warningsData, dailyData, statusData] = await Promise.all([
        api.getMetrics(sessionId),
        api.getCategoryBreakdown(sessionId),
        api.getWarnings(sessionId),
        api.getDailySpending(sessionId),
        api.getSessionStatus(sessionId),
      ]);

      setMetrics(metricsData);
      setCategories(categoriesData);
      setWarnings(warningsData);
      setDailySpending(dailyData);
      setSessionMonth(statusData.selected_month);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      console.error('Dashboard error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
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
            <Button onClick={() => router.push('/upload')}>
              Go to Upload
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!metrics || !categories) {
    return null;
  }

  const formatCurrency = (amount: number) => {
    return amount.toLocaleString('en-IN', { maximumFractionDigits: 0 });
  };

  const getDifferenceTrend = (diff: number) => {
    if (diff > 0) return 'positive';
    if (diff < 0) return 'negative';
    return 'neutral';
  };

  const getDifferenceSubtitle = (diff: number) => {
    if (diff > 0) return 'You paid extra for friends';
    if (diff < 0) return 'Friends paid for you';
    return 'Perfectly balanced';
  };

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
              <p className="text-gray-600 mt-2">Your financial overview</p>
            </div>
            {sessionMonth && (
              <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-lg">
                <Calendar className="w-5 h-5 text-blue-600" />
                <div>
                  <p className="text-xs text-gray-600">Analysis Period</p>
                  <p className="text-sm font-semibold text-gray-900">
                    {formatMonth(sessionMonth)}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Metrics Cards - New 1:2:1 Layout */}
        <div className="grid grid-cols-4 gap-6 mb-8">
          {/* Cash Outflow - 1 column */}
          <div className="col-span-1">
            <MetricCard
              title="Cash Outflow"
              value={formatCurrency(metrics.cash_outflow)}
              subtitle="Total bank debits"
              trend="neutral"
            />
          </div>

          {/* Net Consumption - 2 columns (wider, with nested breakdown) */}
          <div className="col-span-2">
            <Card>
              <CardHeader className="pb-3 text-center">
                <CardTitle className="text-sm font-medium text-gray-600">
                  Net Consumption
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center mb-4">
                  <div className="text-3xl font-bold mb-1">
                    ₹{formatCurrency(metrics.net_consumption.total)}
                  </div>
                  <p className="text-sm text-gray-600">Your true spending</p>
                </div>

                {/* Nested 3 sub-metrics - IMPROVED ALIGNMENT */}
                <div className="grid grid-cols-3 gap-3 mt-4">
                  <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                    <p className="text-xs font-medium text-gray-600 mb-2">
                      Independent<br/> Spends
                    </p>
                    <p className="text-xl font-bold text-gray-900">
                      ₹{formatCurrency(metrics.net_consumption.breakdown.solo_spend)}
                    </p>
                    <p className="text-xs text-gray-500 mt-2">
                      {((metrics.net_consumption.breakdown.solo_spend / metrics.net_consumption.total) * 100).toFixed(0)}%
                    </p>
                  </div>

                  <div className="bg-green-50 p-4 rounded-lg border border-green-100">
                    <p className="text-xs font-medium text-gray-600 mb-2">
                      My Share<br/>(Splits I Paid)
                    </p>
                    <p className="text-xl font-bold text-gray-900">
                      ₹{formatCurrency(metrics.net_consumption.breakdown.split_i_paid)}
                    </p>
                    <p className="text-xs text-gray-500 mt-2">
                      {((metrics.net_consumption.breakdown.split_i_paid / metrics.net_consumption.total) * 100).toFixed(0)}%
                    </p>
                  </div>

                  <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
                    <p className="text-xs font-medium text-gray-600 mb-2">
                      My Share<br/>(Splits Others Paid)
                    </p>
                    <p className="text-xl font-bold text-gray-900">
                      ₹{formatCurrency(metrics.net_consumption.breakdown.split_they_paid)}
                    </p>
                    <p className="text-xs text-gray-500 mt-2">
                      {((metrics.net_consumption.breakdown.split_they_paid / metrics.net_consumption.total) * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Monthly Float - 1 column */}
          <div className="col-span-1">
            <MetricCard
              title="Monthly Float"
              value={formatCurrency(Math.abs(metrics.monthly_float))}
              subtitle={
                Math.abs(metrics.monthly_float) < 100
                  ? 'Perfectly balanced'
                  : metrics.monthly_float > 0
                  ? 'You paid extra'
                  : 'Friends paid extra'
              }
              trend={
                Math.abs(metrics.monthly_float) < 100
                  ? 'neutral'
                  : metrics.monthly_float > 0
                  ? 'positive'
                  : 'negative'
              }
            />
          </div>
        </div>

        {/* Charts - Stacked Vertically */}
        <div className="space-y-6 mb-8">
          {/* Category Chart - Full Width */}
          {categories.categories.length > 0 && (
            <CategoryChart categories={categories.categories} />
          )}

          {/* Daily Spending Chart - Full Width */}
          {dailySpending && dailySpending.daily_spending.length > 0 && (
            <DailySpendingChart data={dailySpending.daily_spending} />
          )}
        </div>

        {/* Warnings */}
        {warnings && warnings.unlinked_payer.count > 0 && (
          <Card className="border-yellow-200 bg-yellow-50 mb-8">
            <CardHeader>
              <CardTitle className="text-yellow-800">⚠️ Potential Double-Counting</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-yellow-700 mb-2">
                You have {warnings.unlinked_payer.count} unlinked split expense(s) totaling{' '}
                ₹{formatCurrency(warnings.unlinked_payer.total_amount)}
              </p>
              <p className="text-sm text-yellow-600">
                These might already be counted in solo expenses. Review them in the transactions page.
              </p>
              <Button
                variant="outline"
                className="mt-4"
                onClick={() => router.push('/transactions')}
              >
                View Transactions
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}