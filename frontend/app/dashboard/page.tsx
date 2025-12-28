// app/dashboard/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useSession } from '@/lib/session-context';
import { api } from '@/lib/api';
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
  const searchParams = useSearchParams();
  const sessionFromUrl = searchParams.get('session');  // ✅ Read from URL
  const { sessions, currentSessionMonth } = useSession();  // ✅ Remove currentSession from here
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [categories, setCategories] = useState<CategoryBreakdown | null>(null);
  const [warnings, setWarnings] = useState<Warnings | null>(null);
  const [dailySpending, setDailySpending] = useState<DailySpendingResponse | null>(null);

  useEffect(() => {
    console.log('🔍 Dashboard useEffect triggered');
    console.log('   sessionFromUrl:', sessionFromUrl);
    console.log('   sessions array:', sessions);
    
    if (!sessionFromUrl) {
      console.log('   ❌ No session in URL, skipping fetch');
      return;
    }
    
    console.log('   ✅ Fetching data for:', sessionFromUrl);
    fetchDashboardData(sessionFromUrl);
  }, [sessionFromUrl]);

  useEffect(() => {
    if (categories) {
      console.log('📊 All categories:', categories.categories.map(c => ({
        category: c.category,
        amount: c.amount,
        count: c.count
      })));
    }
  }, [categories]);

  const fetchDashboardData = async (sessionId: string) => {
    console.log('📊 fetchDashboardData called with:', sessionId);
    
    try {
      setLoading(true);
      setError(null);

      console.log('   🌐 Making API calls...');
      const [metricsData, categoriesData, warningsData, dailyData] = await Promise.all([
        api.getMetrics(sessionId),
        api.getCategoryBreakdown(sessionId),
        api.getWarnings(sessionId),
        api.getDailySpending(sessionId),
      ]);

      console.log('   ✅ API responses received');
      console.log('   📈 Metrics:', metricsData);
      console.log('   📊 Categories:', categoriesData);
      
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
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
              <p className="text-gray-600 mt-2">Your financial overview</p>
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

        {/* Metrics Cards - New 50/50 Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Left: Net Consumption (full height) */}
          <Card className="flex flex-col">
            <CardHeader className="pb-3 text-center">
              <CardTitle className="text-sm font-medium text-gray-600">
                Net Consumption
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1">
              <div className="text-center mb-4">
                <div className="text-3xl font-bold mb-1">
                  ₹{formatCurrency(metrics.net_consumption.total)}
                </div>
                <p className="text-sm text-gray-600">Your true spending</p>
              </div>

              {/* Nested 3 sub-metrics */}
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

          {/* Right: Cash Outflow + Monthly Float stacked */}
          <div className="grid grid-rows-2 gap-6">
            <Card className="flex flex-col">
              <CardHeader className="pb-2 text-center">
                <CardTitle className="text-sm font-medium text-gray-600">Cash Outflow</CardTitle>
              </CardHeader>
              <CardContent className="text-center flex-1 flex flex-col justify-center">
                <div className="text-3xl font-bold">₹{formatCurrency(metrics.cash_outflow)}</div>
                <p className="text-sm text-gray-600 mt-1">Total bank debits</p>
              </CardContent>
            </Card>

            <Card className="flex flex-col">
              <CardHeader className="pb-2 text-center">
                <CardTitle className="text-sm font-medium text-gray-600">Monthly Float</CardTitle>
              </CardHeader>
              <CardContent className="text-center flex-1 flex flex-col justify-center">
                <div className="text-3xl font-bold">₹{formatCurrency(Math.abs(metrics.monthly_float))}</div>
                <p className={`text-sm mt-1 ${
                  Math.abs(metrics.monthly_float) < 100
                    ? 'text-gray-600'
                    : metrics.monthly_float > 0
                    ? 'text-green-600'
                    : 'text-red-600'
                }`}>
                  {Math.abs(metrics.monthly_float) < 100
                    ? 'Perfectly balanced'
                    : metrics.monthly_float > 0
                    ? 'You paid extra'
                    : 'Friends paid extra'}
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
        
        {/* Actionable Warnings - NEW */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Double Counting Warning */}
          <Card 
            className="cursor-pointer hover:shadow-lg transition-all hover:border-orange-300"
            onClick={() => router.push(`/linking?session=${sessionFromUrl}`)}
          >
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-orange-600">
                <span className="text-2xl">⚠️</span>
                Potential Double Counting
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold mb-2">
                {warnings?.unlinked_payer.count || 0}
              </p>
              <p className="text-sm text-gray-600 mb-1">
                Unlinked Splitwise transactions
              </p>
              <p className="text-xs text-gray-500 mb-4">
                Total: ₹{formatCurrency(warnings?.unlinked_payer.total_amount || 0)}
              </p>
              <p className="text-sm text-blue-600 flex items-center gap-1 font-medium">
                Review and link transactions <span>→</span>
              </p>
            </CardContent>
          </Card>

          {/* Uncategorized Transactions Warning */}
          <Card 
            className="cursor-pointer hover:shadow-lg transition-all hover:border-amber-300"
            onClick={() => router.push(`/transactions?session=${sessionFromUrl}&category=Other`)}
          >
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-amber-600">
                <span className="text-2xl">📝</span>
                Uncategorized Transactions
              </CardTitle>
            </CardHeader>
            <CardContent>
              {(() => {
                const otherCategory = categories?.categories.find(c => c.category === 'Other');
                return (
                  <>
                    <p className="text-3xl font-bold mb-2">
                      {otherCategory?.count || 0}
                    </p>
                    <p className="text-sm text-gray-600 mb-1">
                      Transactions need categorization
                    </p>
                    <p className="text-xs text-gray-500 mb-4">
                      Total: ₹{formatCurrency(otherCategory?.amount || 0)}
                    </p>
                    <p className="text-sm text-blue-600 flex items-center gap-1 font-medium">
                      Manually Categorize <span>→</span>
                    </p>
                  </>
                );
              })()}
            </CardContent>
          </Card>
        </div>

        {/* Charts - Side by Side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Left: Category Chart */}
          {categories.categories.length > 0 && (
            <CategoryChart categories={categories.categories} />
          )}

          {/* Right: Daily Spending Chart */}
          {dailySpending && dailySpending.daily_spending.length > 0 && (
            <DailySpendingChart data={dailySpending.daily_spending} />
          )}
        </div>
      </div>
    </div>
  );
}