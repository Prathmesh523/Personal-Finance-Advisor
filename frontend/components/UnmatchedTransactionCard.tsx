// components/UnmatchedTransactionCard.tsx

'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { UnmatchedSplitwise } from '@/types';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

interface UnmatchedTransactionCardProps {
  transaction: UnmatchedSplitwise;
  onLink: (splitwiseId: number, bankId: number) => void;
  onSkip: (splitwiseId: number, reason: string) => void;
  loading: boolean;
}

export function UnmatchedTransactionCard({
  transaction,
  onLink,
  onSkip,
  loading,
}: UnmatchedTransactionCardProps) {
  const [selectedBankId, setSelectedBankId] = useState<number | null>(
    transaction.preselect_id
  );

  const formatCurrency = (amount: number) => {
    return amount.toLocaleString('en-IN', { maximumFractionDigits: 0 });
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  const getScoreBadge = (score: number) => {
    if (score >= 0.85) {
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800 font-medium">
          {Math.round(score * 100)}% match
        </span>
      );
    } else if (score >= 0.70) {
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800 font-medium">
          {Math.round(score * 100)}% match
        </span>
      );
    } else {
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-orange-100 text-orange-800 font-medium">
          {Math.round(score * 100)}% match
        </span>
      );
    }
  };

  const handleLink = () => {
    if (selectedBankId) {
      onLink(transaction.id, selectedBankId);
    }
  };

  const handleSkip = () => {
    onSkip(transaction.id, 'no_match_found');
  };

  return (
    <Card className="border-2 border-orange-200 bg-orange-50">
      <CardContent className="p-6">
        {/* Splitwise Transaction Header */}
        <div className="flex items-start justify-between mb-4 pb-4 border-b border-orange-200">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🍕</span>
              <div>
                <p className="font-semibold text-gray-900">{transaction.description}</p>
                <p className="text-sm text-gray-600">
                  {formatDate(transaction.date)} • {transaction.category || 'Uncategorized'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-4 text-sm mt-2">
              <span className="text-gray-700">
                Total Bill: <span className="font-semibold">₹{formatCurrency(transaction.total_cost)}</span>
              </span>
              <span className="text-gray-700">
                Your Share: <span className="font-semibold">₹{formatCurrency(transaction.my_share)}</span>
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 text-orange-600">
            <AlertCircle className="w-5 h-5" />
            <span className="text-sm font-medium">Unmatched</span>
          </div>
        </div>

        {/* Suggested Matches */}
        <div className="space-y-3">
          <p className="text-sm font-medium text-gray-700 mb-3">
            Suggested Bank Matches:
          </p>

          {transaction.suggested_matches.length > 0 ? (
            <>
              {transaction.suggested_matches.map((match) => (
                <label
                  key={match.id}
                  className={`flex items-center gap-3 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                    selectedBankId === match.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name={`match-${transaction.id}`}
                    value={match.id}
                    checked={selectedBankId === match.id}
                    onChange={() => setSelectedBankId(match.id)}
                    className="w-4 h-4 text-blue-600"
                    disabled={loading}
                  />
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <p className="font-medium text-gray-900">{match.description}</p>
                      {getScoreBadge(match.match_score)}
                    </div>
                    <div className="flex items-center gap-3 text-sm text-gray-600">
                      <span>{formatDate(match.date)}</span>
                      <span>•</span>
                      <span className="font-semibold">₹{formatCurrency(Math.abs(match.amount))}</span>
                      <span>•</span>
                      <span className="text-xs italic">{match.match_reason}</span>
                    </div>
                  </div>
                </label>
              ))}

              {/* None of these option */}
              <label
                className={`flex items-center gap-3 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                  selectedBankId === null
                    ? 'border-gray-500 bg-gray-50'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name={`match-${transaction.id}`}
                  value="none"
                  checked={selectedBankId === null}
                  onChange={() => setSelectedBankId(null)}
                  className="w-4 h-4 text-gray-600"
                  disabled={loading}
                />
                <span className="text-gray-700">None of these match (paid with cash/other method)</span>
              </label>
            </>
          ) : (
            <div className="text-center py-6 text-gray-500">
              <p>No potential matches found</p>
              <p className="text-sm mt-1">This transaction might have been paid with cash or another method</p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 mt-6 pt-4 border-t border-orange-200">
          <Button
            onClick={handleLink}
            disabled={selectedBankId === null || loading}
            className="flex-1"
          >
            {loading ? 'Linking...' : 'Link Selected'}
          </Button>
          <Button
            onClick={handleSkip}
            variant="outline"
            disabled={loading}
            className="flex-1"
          >
            {loading ? 'Skipping...' : 'Skip This'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}