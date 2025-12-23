// app/compare/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@/lib/session-context';
import { api } from '@/lib/api';
import { formatMonth } from '@/lib/utils';
import { AvailableSession, ComparisonResponse } from '@/types';
import { ComparisonMetricCard } from '@/components/ComparisonMetricCard';
import { CategoryComparisonChart } from '@/components/CategoryComparisonChart';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';

export default function ComparePage() {
  const router = useRouter();
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { sessions, loading } = useSession();
  const availableSessions = sessions.filter(s => s.status === 'completed');

  const [session1, setSession1] = useState<string>('');
  const [session2, setSession2] = useState<string>('');
  const [comparisonData, setComparisonData] = useState<ComparisonResponse | null>(null);


  const handleCompare = async () => {
    if (!session1 || !session2) {
      alert('Please select both months');
      return;
    }

    if (session1 === session2) {
      alert('Please select different months');
      return;
    }

    try {
      setComparing(true);
      setError(null);

      const data = await api.compareSessions(session1, session2);
      setComparisonData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Comparison failed');
      console.error('Comparison error:', err);
    } finally {
      setComparing(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return amount.toLocaleString('en-IN', { maximumFractionDigits: 0 });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading sessions...</p>
        </div>
      </div>
    );
  }

  // Not enough sessions
  if (availableSessions.length < 2) {
    return (
      <div className="min-h-screen p-8">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Compare Months</h1>
            <p className="text-gray-600 mt-2">Compare your spending across different months</p>
          </div>

          <Card className="max-w-2xl mx-auto">
            <CardContent className="py-12 text-center">
              <AlertCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Not Enough Data
              </h3>
              <p className="text-gray-600 mb-6">
                You need at least 2 months of data to compare.
                {availableSessions.length === 1 && ' You currently have 1 month analyzed.'}
                {availableSessions.length === 0 && ' Upload your first month to get started.'}
              </p>
              <Button onClick={() => router.push('/upload')}>
                Upload New Month
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Compare Months</h1>
          <p className="text-gray-600 mt-2">Compare your spending across different months</p>
        </div>

        {/* Month Selectors */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Select Months to Compare</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Month 1 */}
              <div className="space-y-2">
                <label className="text-sm font-medium">First Month</label>
                <Select value={session1} onValueChange={setSession1}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select month" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableSessions.map((session) => (
                      <SelectItem key={session.id} value={session.id}>
                        {formatMonth(session.month)} ({session.transaction_count} txns)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Month 2 */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Second Month</label>
                <Select value={session2} onValueChange={setSession2}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select month" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableSessions.map((session) => (
                      <SelectItem key={session.id} value={session.id}>
                        {formatMonth(session.month)} ({session.transaction_count} txns)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Compare Button */}
              <div className="space-y-2">
                <label className="text-sm font-medium invisible">Action</label>
                <Button
                  onClick={handleCompare}
                  disabled={!session1 || !session2 || comparing}
                  className="w-full"
                >
                  {comparing ? 'Comparing...' : 'Compare'}
                </Button>
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-600 mt-4">{error}</p>
            )}
          </CardContent>
        </Card>

        {/* Comparison Results */}
        {comparisonData && (
          <div className="space-y-8">
            {/* Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <ComparisonMetricCard
                title="Net Consumption"
                value1={comparisonData.net_consumption.session1_value}
                value2={comparisonData.net_consumption.session2_value}
                difference={comparisonData.net_consumption.difference}
                percentageChange={comparisonData.net_consumption.percentage_change}
                month1={comparisonData.session1_month}
                month2={comparisonData.session2_month}
              />
              <ComparisonMetricCard
                title="Cash Outflow"
                value1={comparisonData.cash_outflow.session1_value}
                value2={comparisonData.cash_outflow.session2_value}
                difference={comparisonData.cash_outflow.difference}
                percentageChange={comparisonData.cash_outflow.percentage_change}
                month1={comparisonData.session1_month}
                month2={comparisonData.session2_month}
              />
              <ComparisonMetricCard
                title="Monthly Float"
                value1={comparisonData.monthly_float.session1_value}
                value2={comparisonData.monthly_float.session2_value}
                difference={comparisonData.monthly_float.difference}
                percentageChange={comparisonData.monthly_float.percentage_change}
                month1={comparisonData.session1_month}
                month2={comparisonData.session2_month}
              />
            </div>

            {/* Category Comparison Chart */}
            <CategoryComparisonChart
              data={comparisonData.category_comparison}
              month1={comparisonData.session1_month}
              month2={comparisonData.session2_month}
            />

            {/* Top Movers */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Top Increases */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-red-600" />
                    Biggest Increases
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {comparisonData.top_increases.length > 0 ? (
                    <div className="space-y-3">
                      {comparisonData.top_increases.map((item, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-3 bg-red-50 rounded-lg"
                        >
                          <div>
                            <p className="font-medium text-gray-900">{item.category}</p>
                            <p className="text-xs text-gray-600">
                              ₹{formatCurrency(item.session1_amount)} → ₹{formatCurrency(item.session2_amount)}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-semibold text-red-600">
                              +₹{formatCurrency(item.difference)}
                            </p>
                            <p className="text-xs text-gray-600">
                              +{item.percentage_change.toFixed(1)}%
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 text-center py-4">
                      No increases found
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* Top Decreases */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingDown className="w-5 h-5 text-green-600" />
                    Biggest Decreases
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {comparisonData.top_decreases.length > 0 ? (
                    <div className="space-y-3">
                      {comparisonData.top_decreases.map((item, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-3 bg-green-50 rounded-lg"
                        >
                          <div>
                            <p className="font-medium text-gray-900">{item.category}</p>
                            <p className="text-xs text-gray-600">
                              ₹{formatCurrency(item.session1_amount)} → ₹{formatCurrency(item.session2_amount)}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-semibold text-green-600">
                              ₹{formatCurrency(Math.abs(item.difference))}
                            </p>
                            <p className="text-xs text-gray-600">
                              {item.percentage_change.toFixed(1)}%
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 text-center py-4">
                      No decreases found
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Daily Average */}
            <Card>
              <CardHeader>
                <CardTitle>Daily Spending Average</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-8">
                  <div>
                    <p className="text-sm text-gray-600">
                      {formatMonth(comparisonData.session1_month)}
                    </p>
                    <p className="text-2xl font-bold text-gray-900">
                      ₹{formatCurrency(comparisonData.session1_daily_avg)}/day
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">
                      {formatMonth(comparisonData.session2_month)}
                    </p>
                    <p className="text-2xl font-bold text-gray-900">
                      ₹{formatCurrency(comparisonData.session2_daily_avg)}/day
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Empty State */}
        {!comparisonData && !comparing && (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-gray-500">
                Select two months above to see the comparison
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}