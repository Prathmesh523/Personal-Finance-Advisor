// components/RecurringSubscriptionsCard.tsx

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { RecurringSummary } from '@/types';

interface RecurringSubscriptionsCardProps {
  data: RecurringSummary;
}

export function RecurringSubscriptionsCard({ data }: RecurringSubscriptionsCardProps) {
  const formatCurrency = (amount: number) => {
    return amount.toLocaleString('en-IN', { maximumFractionDigits: 0 });
  };

  if (data.count === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            📊 Recurring Subscriptions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            No recurring subscriptions detected yet.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          📊 Recurring Subscriptions
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600">
              {data.count} active subscription{data.count !== 1 ? 's' : ''}
            </p>
            <p className="text-2xl font-bold text-gray-900">
              ₹{formatCurrency(data.monthly_total)}/month
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-600">Annual</p>
            <p className="text-xl font-semibold text-gray-700">
              ₹{formatCurrency(data.annual_total)}
            </p>
          </div>
        </div>

        {/* Top Subscriptions */}
        <div className="space-y-2 pt-4 border-t">
          <p className="text-sm font-medium text-gray-700">Top subscriptions:</p>
          {data.subscriptions.slice(0, 5).map((sub, index) => (
            <div
              key={index}
              className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg"
            >
              <span className="font-medium text-gray-900">{sub.merchant}</span>
              <span className="text-gray-700">
                ₹{formatCurrency(sub.average_amount)}/mo
              </span>
            </div>
          ))}
        </div>

        {/* Recommendation */}
        <div className="pt-4 border-t">
          <p className="text-sm text-blue-700">
            💡 Review regularly to avoid paying for unused services
          </p>
        </div>
      </CardContent>
    </Card>
  );
}