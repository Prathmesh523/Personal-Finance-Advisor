// components/GroupedTransactionList.tsx

'use client';

import { TransactionGroup } from '@/types';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  ShoppingBag,
  Utensils,
  Car,
  Home,
  CreditCard,
  TrendingUp,
  HelpCircle,
} from 'lucide-react';

interface GroupedTransactionListProps {
  groups: TransactionGroup[];
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

const categoryIcons: Record<string, any> = {
  'Food & Dining': Utensils,
  'Groceries': ShoppingBag,
  'Transport': Car,
  'Shopping': ShoppingBag,
  'Bills & Utilities': Home,
  'Investment': TrendingUp,
  'Settlement': CreditCard,
  'Other': HelpCircle,
};

export function GroupedTransactionList({
  groups,
  currentPage,
  totalPages,
  onPageChange,
}: GroupedTransactionListProps) {
  const formatCurrency = (amount: number) => {
    const isNegative = amount < 0;
    const absAmount = Math.abs(amount);
    return `${isNegative ? '-' : '+'}₹${absAmount.toLocaleString('en-IN', {
      maximumFractionDigits: 0,
    })}`;
  };

  const formatDateHeader = (dateStr: string) => {
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString('en-IN', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      });
    }
  };

  const getCategoryIcon = (category: string | null) => {
    const Icon = categoryIcons[category || 'Other'] || HelpCircle;
    return Icon;
  };

  const getSourceColor = (source: string) => {
    return source === 'BANK' ? 'bg-purple-100' : 'bg-orange-100';
  };

  if (groups.length === 0) {
    return (
      <Card>
        <CardContent className="py-12">
          <p className="text-center text-gray-500">No transactions found</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {groups.map((group) => (
        <Card key={group.date}>
          <CardContent className="p-6">
            {/* Date Header */}
            <div className="flex items-center justify-between mb-4 pb-3 border-b">
              <h3 className="text-lg font-semibold text-gray-900">
                {formatDateHeader(group.date)}
              </h3>
              <div className="text-right">
                <p className="text-sm text-gray-500">{group.count} transactions</p>
                <p
                  className={`text-lg font-semibold ${
                    group.total_amount < 0 ? 'text-red-600' : 'text-green-600'
                  }`}
                >
                  {formatCurrency(group.total_amount)}
                </p>
              </div>
            </div>

            {/* Transactions */}
            <div className="space-y-3">
              {group.transactions.map((txn) => {
                const Icon = getCategoryIcon(txn.category);
                return (
                  <div
                    key={txn.id}
                    className="flex items-center gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    {/* Icon */}
                    <div className={`p-2 rounded-full ${getSourceColor(txn.source)}`}>
                      <Icon className="w-5 h-5 text-gray-700" />
                    </div>

                    {/* Details */}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 truncate">
                        {txn.description}
                      </p>
                      <p className="text-sm text-gray-500">
                        {txn.category || 'Uncategorized'} • {txn.source}
                      </p>
                    </div>

                    {/* Amount */}
                    <div className="text-right">
                      <p
                        className={`font-semibold ${
                          txn.amount < 0 ? 'text-red-600' : 'text-green-600'
                        }`}
                      >
                        {formatCurrency(txn.amount)}
                      </p>
                      {txn.status === 'LINKED' && (
                        <span className="text-xs text-green-600">Linked</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      ))}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Page {currentPage} of {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage === 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}