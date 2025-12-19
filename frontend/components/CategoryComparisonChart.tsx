// components/CategoryComparisonChart.tsx

'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CategoryComparison } from '@/types';

interface CategoryComparisonChartProps {
  data: CategoryComparison[];
  month1: string;
  month2: string;
}

export function CategoryComparisonChart({ data, month1, month2 }: CategoryComparisonChartProps) {
  const formatMonth = (monthStr: string) => {
    const [year, month] = monthStr.split('-');
    const date = new Date(parseInt(year), parseInt(month) - 1);
    return date.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
  };

  // Take top 10 categories
  const chartData = data.slice(0, 10).map((item) => ({
    category: item.category.length > 15 ? item.category.substring(0, 15) + '...' : item.category,
    fullCategory: item.category,
    [formatMonth(month1)]: item.session1_amount,
    [formatMonth(month2)]: item.session2_amount,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border rounded shadow-lg">
          <p className="font-semibold mb-2">{payload[0].payload.fullCategory}</p>
          <p className="text-sm text-blue-600">
            {payload[0].name}: ₹{payload[0].value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
          <p className="text-sm text-green-600">
            {payload[1].name}: ₹{payload[1].value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Category Comparison</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              dataKey="category" 
              tick={{ fontSize: 12 }} 
              angle={-45}
              textAnchor="end"
              height={100}
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Bar dataKey={formatMonth(month1)} fill="#3b82f6" radius={[4, 4, 0, 0]} />
            <Bar dataKey={formatMonth(month2)} fill="#10b981" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}