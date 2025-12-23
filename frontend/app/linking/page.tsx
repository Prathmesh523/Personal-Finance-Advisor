// app/linking/page.tsx

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { storage } from '@/lib/storage';
import { UnmatchedSplitwise } from '@/types';
import { UnmatchedTransactionCard } from '@/components/UnmatchedTransactionCard';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle2, Calendar } from 'lucide-react';
import { formatMonth } from '@/lib/utils';

export default function LinkingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [sessionMonth, setSessionMonth] = useState<string | null>(null);
  const [unmatched, setUnmatched] = useState<UnmatchedSplitwise[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [viewMode, setViewMode] = useState<'one-at-a-time' | 'all'>('one-at-a-time');

  useEffect(() => {
    const sessionId = storage.getSessionId();

    if (!sessionId) {
      router.push('/upload');
      return;
    }

    fetchUnmatched(sessionId);
  }, [router]);

  const fetchUnmatched = async (sessionId: string) => {
    try {
      setLoading(true);
      setError(null);

      const [unmatchedData, statusData] = await Promise.all([
        api.getUnmatchedSplitwise(sessionId),
        api.getSessionStatus(sessionId),
      ]);

      setUnmatched(unmatchedData.unmatched);
      setSessionMonth(statusData.selected_month);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load unmatched transactions');
      console.error('Linking page error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLink = async (splitwiseId: number, bankId: number) => {
    const sessionId = storage.getSessionId();
    if (!sessionId) return;

    try {
      setProcessing(true);
      setError(null);

      await api.linkTransactionsManually(sessionId, splitwiseId, bankId);

      // Remove from list
      const newUnmatched = unmatched.filter((t) => t.id !== splitwiseId);
      setUnmatched(newUnmatched);

      // Move to next or adjust index
      if (currentIndex >= newUnmatched.length && currentIndex > 0) {
        setCurrentIndex(currentIndex - 1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to link transactions');
      console.error('Link error:', err);
    } finally {
      setProcessing(false);
    }
  };

  const handleSkip = async (splitwiseId: number, reason: string) => {
    const sessionId = storage.getSessionId();
    if (!sessionId) return;

    try {
      setProcessing(true);
      setError(null);

      await api.skipTransaction(sessionId, splitwiseId, reason);

      // Remove from list
      const newUnmatched = unmatched.filter((t) => t.id !== splitwiseId);
      setUnmatched(newUnmatched);

      // Move to next or adjust index
      if (currentIndex >= newUnmatched.length && currentIndex > 0) {
        setCurrentIndex(currentIndex - 1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to skip transaction');
      console.error('Skip error:', err);
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading unmatched transactions...</p>
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
            <Button onClick={() => router.push('/dashboard')}>Back to Dashboard</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // All done!
  if (unmatched.length === 0) {
    return (
      <div className="min-h-screen p-8">
        <div className="max-w-4xl mx-auto">
          <Card className="border-green-200 bg-green-50">
            <CardContent className="py-12 text-center">
              <CheckCircle2 className="w-16 h-16 text-green-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-green-800 mb-2">All Done!</h2>
              <p className="text-green-700 mb-6">
                No unmatched transactions found. All your Splitwise expenses are linked or marked as skipped.
              </p>
              <Button onClick={() => router.push('/dashboard')}>Back to Dashboard</Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const currentTransaction = unmatched[currentIndex];

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Link Transactions</h1>
              <p className="text-gray-600 mt-2">Match Splitwise expenses to bank transactions</p>
            </div>
            {sessionMonth && (
              <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 rounded-lg">
                <Calendar className="w-5 h-5 text-blue-600" />
                <div>
                  <p className="text-xs text-gray-600">Analysis Period</p>
                  <p className="text-sm font-semibold text-gray-900">{formatMonth(sessionMonth)}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Progress */}
        <Card className="mb-6">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">
                  {unmatched.length} unmatched transaction{unmatched.length !== 1 ? 's' : ''} need your review
                </p>
                {viewMode === 'one-at-a-time' && (
                  <p className="text-xs text-gray-500 mt-1">
                    Reviewing {currentIndex + 1} of {unmatched.length}
                  </p>
                )}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setViewMode(viewMode === 'one-at-a-time' ? 'all' : 'one-at-a-time')
                }
              >
                {viewMode === 'one-at-a-time' ? 'View All' : 'One at a Time'}
              </Button>
            </div>
            {viewMode === 'one-at-a-time' && (
              <div className="w-full bg-gray-200 rounded-full h-2 mt-3">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${((currentIndex + 1) / unmatched.length) * 100}%` }}
                />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Transactions */}
        {viewMode === 'one-at-a-time' ? (
          <div className="space-y-4">
            <UnmatchedTransactionCard
              transaction={currentTransaction}
              onLink={handleLink}
              onSkip={handleSkip}
              loading={processing}
            />

            {/* Navigation */}
            {unmatched.length > 1 && (
              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
                  disabled={currentIndex === 0 || processing}
                >
                  ← Previous
                </Button>
                <span className="text-sm text-gray-600">
                  {currentIndex + 1} of {unmatched.length}
                </span>
                <Button
                  variant="outline"
                  onClick={() => setCurrentIndex(Math.min(unmatched.length - 1, currentIndex + 1))}
                  disabled={currentIndex === unmatched.length - 1 || processing}
                >
                  Next →
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {unmatched.map((transaction) => (
              <UnmatchedTransactionCard
                key={transaction.id}
                transaction={transaction}
                onLink={handleLink}
                onSkip={handleSkip}
                loading={processing}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}