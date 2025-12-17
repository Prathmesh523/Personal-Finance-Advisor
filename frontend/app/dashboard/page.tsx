// app/dashboard/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { storage } from '@/lib/storage';
import { Metrics, CategoryBreakdown, Warnings, DailySpendingResponse } from '@/types';
import { MetricCard } from '@/components/MetricCard';
import { CategoryChart } from '@/components/CategoryChart';
import { DailySpendingChart } from '@/components/DailySpendingChart';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [categories, setCategories] = useState<CategoryBreakdown | null>(null);
  const [warnings, setWarnings] = useState<Warnings | null>(null);
  const [dailySpending, setDailySpending] = useState<DailySpendingResponse | null>(null);

  useEffect(() => {
    const sessionId = storage.getSessionId();
    
    if (!sessionId) {
      router.push('/upload');
      return;
    }

    fetchDashboardData(sessionId);
  }, [router]);

  const fetchDashboardData = async (sessionId: string) => {
    try {
      setLoading(true);
      setError(null);

      const [metricsData, categoriesData, warningsData, dailyData] = await Promise.all([
        api.getMetrics(sessionId),
        api.getCategories(sessionId),
        api.getWarnings(sessionId),
        api.getDailySpending(sessionId),
      ]);

      setMetrics(metricsData);
      setCategories(categoriesData);
      setWarnings(warningsData);
      setDailySpending(dailyData);
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
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-2">Your financial overview</p>
        </div>

        {/* Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <MetricCard
            title="Net Consumption"
            value={formatCurrency(metrics.net_consumption.total)}
            subtitle="Your true spending"
          />
          <MetricCard
            title="Cash Outflow"
            value={formatCurrency(metrics.cash_outflow)}
            subtitle="Money that left your account"
          />
          <MetricCard
            title="Difference"
            value={formatCurrency(Math.abs(metrics.difference))}
            subtitle={getDifferenceSubtitle(metrics.difference)}
            trend={getDifferenceTrend(metrics.difference)}
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Daily Spending Chart */}
          {dailySpending && dailySpending.daily_spending.length > 0 && (
            <DailySpendingChart data={dailySpending.daily_spending} />
          )}

          {/* Category Chart */}
          {categories.categories.length > 0 && (
            <CategoryChart categories={categories.categories} />
          )}
        </div>

        {/* Breakdown */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Consumption Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-gray-600">Solo Expenses</p>
                <p className="text-2xl font-semibold">
                  ₹{formatCurrency(metrics.net_consumption.breakdown.solo)}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Split (You Paid)</p>
                <p className="text-2xl font-semibold">
                  ₹{formatCurrency(metrics.net_consumption.breakdown.split_you_paid)}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Split (Friend Paid)</p>
                <p className="text-2xl font-semibold">
                  ₹{formatCurrency(metrics.net_consumption.breakdown.split_friend_paid)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

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