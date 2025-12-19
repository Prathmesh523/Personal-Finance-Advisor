// components/DailySpendingChart.tsx

'use client';

import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DailySpendingItem } from '@/types';
import { AlertTriangle } from 'lucide-react';

interface DailySpendingChartProps {
  data: DailySpendingItem[];
}

const CHART_LIMIT = 10000; // ₹10k cap

export function DailySpendingChart({ data }: DailySpendingChartProps) {
  // Separate normal days vs outliers
  const normalDays = data.filter(item => item.amount <= CHART_LIMIT);
  const outliers = data.filter(item => item.amount > CHART_LIMIT);

  // Format data for chart (capped at 10k)
  const chartData = data.map((item) => ({
    date: new Date(item.date).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
    }),
    fullDate: new Date(item.date).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }),
    amount: Math.min(item.amount, CHART_LIMIT), // Cap at 10k for chart
    actualAmount: item.amount, // Keep original for tooltip
    count: item.count,
    isCapped: item.amount > CHART_LIMIT,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border rounded shadow-lg">
          <p className="font-semibold">{data.fullDate}</p>
          <p className="text-sm text-gray-600">
            ₹{data.actualAmount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
          <p className="text-xs text-gray-500">
            {data.count} transaction{data.count !== 1 ? 's' : ''}
          </p>
          {data.isCapped && (
            <p className="text-xs text-orange-600 mt-1">
              ⚠️ Exceeds chart limit
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Daily Spending</CardTitle>
        <p className="text-xs text-gray-500 mt-1">
          Chart capped at ₹{(CHART_LIMIT / 1000).toFixed(0)}k for better visibility
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Bar Chart */}
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              stroke="#888"
            />
            <YAxis
              tick={{ fontSize: 12 }}
              stroke="#888"
              tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}k`}
              domain={[0, CHART_LIMIT]}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar 
              dataKey="amount" 
              radius={[4, 4, 0, 0]}
              fill="#3b82f6"
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.isCapped ? '#ef4444' : '#3b82f6'} 
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Outliers Section */}
        {outliers.length > 0 && (
          <div className="border-t pt-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-5 h-5 text-orange-600" />
              <h4 className="font-semibold text-gray-900">
                High Spending Days ({outliers.length})
              </h4>
            </div>
            <p className="text-xs text-gray-500 mb-3">
              Days with spending above ₹{(CHART_LIMIT / 1000).toFixed(0)}k (likely transfers/rent)
            </p>
            <div className="space-y-2">
              {outliers.map((item, index) => {
                const date = new Date(item.date);
                return (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 bg-orange-50 border border-orange-200 rounded-lg"
                  >
                    <div>
                      <p className="font-medium text-gray-900">
                        {date.toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'long',
                          year: 'numeric',
                        })}
                      </p>
                      <p className="text-xs text-gray-600">
                        {item.count} transaction{item.count !== 1 ? 's' : ''}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-orange-600">
                        ₹{item.amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </p>
                      <p className="text-xs text-gray-500">
                        +₹{(item.amount - CHART_LIMIT).toLocaleString('en-IN', { maximumFractionDigits: 0 })} over limit
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}