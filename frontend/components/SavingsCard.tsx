// components/SavingsCard.tsx

'use client';

import { useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CategoryDecrease } from '@/types';
import { TrendingDown } from 'lucide-react';

interface SavingsCardProps {
  categories: CategoryDecrease[];
}

export function SavingsCard({ categories }: SavingsCardProps) {
  const router = useRouter();

  const formatCurrency = (amount: number) => {
    return amount.toLocaleString('en-IN', { maximumFractionDigits: 0 });
  };

  const handleViewTransactions = (category: string) => {
    router.push(`/transactions?category=${encodeURIComponent(category)}`);
  };

  if (categories.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            ✅ Great Savings!
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            No major decreases detected. Keep tracking to find opportunities!
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          ✅ Great Savings!
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {categories.map((cat, index) => (
          <div
            key={index}
            className={`p-4 border rounded-lg ${
              index < categories.length - 1 ? 'border-b' : ''
            }`}
          >
            {/* Category Header */}
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-semibold text-gray-900">{cat.category}</h3>
              <div className="flex items-center gap-1 text-green-600">
                <TrendingDown className="w-4 h-4" />
                <span className="text-sm font-medium">
                  -{cat.change_percentage}%
                </span>
              </div>
            </div>

            {/* Amount */}
            <p className="text-2xl font-bold text-gray-900 mb-1">
              ₹{formatCurrency(cat.current)}
            </p>
            <p className="text-sm text-gray-600 mb-3">
              vs ₹{formatCurrency(cat.previous)} last month
            </p>

            {/* Savings Badge */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-3">
              <p className="text-sm text-green-900">
                💡 Excellent! Saved ₹{formatCurrency(cat.saved)} this month 🎉
              </p>
            </div>

            {/* View Button */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleViewTransactions(cat.category)}
              className="w-full"
            >
              View Transactions →
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}