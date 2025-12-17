// components/MetricCard.tsx

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: 'positive' | 'negative' | 'neutral';
}

export function MetricCard({ title, value, subtitle, trend }: MetricCardProps) {
  const getTrendColor = () => {
    if (!trend) return 'text-gray-600';
    if (trend === 'positive') return 'text-green-600';
    if (trend === 'negative') return 'text-red-600';
    return 'text-gray-600';
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-600">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold">₹{value}</div>
        {subtitle && (
          <p className={`text-sm mt-1 ${getTrendColor()}`}>{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}