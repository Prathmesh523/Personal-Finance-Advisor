// components/CategoryChart.tsx

'use client';

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CategoryItem } from '@/types';

interface CategoryChartProps {
  categories: CategoryItem[];
}

const COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#84cc16', // lime
];

export function CategoryChart({ categories }: CategoryChartProps) {
  // Take top 8 categories, group rest as "Other"
  const topCategories = categories.slice(0, 7);
  const remaining = categories.slice(7);
  
  const chartData = topCategories.map((cat) => ({
    name: cat.category,
    value: cat.amount,
    percentage: cat.percentage,
  }));

  if (remaining.length > 0) {
    const otherTotal = remaining.reduce((sum, cat) => sum + cat.amount, 0);
    const otherPercentage = remaining.reduce((sum, cat) => sum + cat.percentage, 0);
    chartData.push({
      name: 'Other',
      value: otherTotal,
      percentage: otherPercentage,
    });
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border rounded shadow-lg">
          <p className="font-semibold">{payload[0].name}</p>
          <p className="text-sm text-gray-600">
            ₹{payload[0].value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
          <p className="text-sm text-gray-500">
            {payload[0].payload.percentage.toFixed(1)}%
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Spending by Category</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend 
              verticalAlign="bottom" 
              height={36}
              formatter={(value, entry: any) => (
                `${value} (${entry.payload.percentage.toFixed(1)}%)`
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}