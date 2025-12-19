// components/ComparisonMetricCard.tsx

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface ComparisonMetricCardProps {
  title: string;
  value1: number;
  value2: number;
  difference: number;
  percentageChange: number;
  month1: string;
  month2: string;
}

export function ComparisonMetricCard({
  title,
  value1,
  value2,
  difference,
  percentageChange,
  month1,
  month2,
}: ComparisonMetricCardProps) {
  const formatCurrency = (amount: number) => {
    return amount.toLocaleString('en-IN', { maximumFractionDigits: 0 });
  };

  const getTrendIcon = () => {
    if (Math.abs(percentageChange) < 1) return <Minus className="w-4 h-4" />;
    if (difference > 0) return <ArrowUp className="w-4 h-4" />;
    return <ArrowDown className="w-4 h-4" />;
  };

  const getTrendColor = () => {
    if (Math.abs(percentageChange) < 1) return 'text-gray-500';
    if (difference > 0) return 'text-red-600';
    return 'text-green-600';
  };

  const formatMonth = (monthStr: string) => {
    const [year, month] = monthStr.split('-');
    const date = new Date(parseInt(year), parseInt(month) - 1);
    return date.toLocaleDateString('en-IN', { month: 'short' });
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-600">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* Values */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500">{formatMonth(month1)}</p>
              <p className="text-lg font-semibold">₹{formatCurrency(value1)}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500">{formatMonth(month2)}</p>
              <p className="text-lg font-semibold">₹{formatCurrency(value2)}</p>
            </div>
          </div>

          {/* Change Indicator */}
          <div className={`flex items-center gap-2 ${getTrendColor()}`}>
            {getTrendIcon()}
            <span className="text-sm font-medium">
              {difference >= 0 ? '+' : ''}₹{formatCurrency(Math.abs(difference))}
            </span>
            <span className="text-xs">
              ({percentageChange >= 0 ? '+' : ''}{percentageChange.toFixed(1)}%)
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}