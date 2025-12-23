// app/recommendations/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSession } from '@/lib/session-context';
import { api } from '@/lib/api';
import { formatMonth } from '@/lib/utils';
import { RecommendationsResponse } from '@/types';
import { RecurringSubscriptionsCard } from '@/components/RecurringSubscriptionsCard';
import { HighSpendingCard } from '@/components/HighSpendingCard';
import { SavingsCard } from '@/components/SavingsCard';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Calendar } from 'lucide-react';

export default function RecommendationsPage() {
  const router = useRouter();
  const { currentSession, currentSessionMonth } = useSession();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<RecommendationsResponse | null>(null);

  useEffect(() => {
    if (!currentSession) return;
    fetchRecommendations(currentSession);
  }, [router, currentSession]);

  const fetchRecommendations = async (sessionId: string) => {
    try {
      setLoading(true);
      setError(null);

      const recommendations = await api.getRecommendations(sessionId);
      setData(recommendations);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recommendations');
      console.error('Recommendations error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading recommendations...</p>
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

  if (!data) {
    return null;
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">💡 Recommendations</h1>
              <p className="text-gray-600 mt-2">
                Personalized insights based on your spending
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

        {/* Recommendations Cards */}
        <div className="space-y-6">
          {/* Recurring Subscriptions */}
          <RecurringSubscriptionsCard data={data.recurring} />

          {/* High Spending */}
          <HighSpendingCard categories={data.high_spending} />

          {/* Savings */}
          <SavingsCard categories={data.savings} />
        </div>
      </div>
    </div>
  );
}