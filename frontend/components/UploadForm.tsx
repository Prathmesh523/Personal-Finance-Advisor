// components/UploadForm.tsx

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface UploadFormProps {
  onSubmit: (
    bankFile: File,
    splitwiseFile: File,
    month: number,
    year: number
  ) => void;
  loading: boolean;
}

export function UploadForm({ onSubmit, loading }: UploadFormProps) {
  const [bankFile, setBankFile] = useState<File | null>(null);
  const [splitwiseFile, setSplitWiseFile] = useState<File | null>(null);
  const [month, setMonth] = useState<number>(new Date().getMonth() + 1);
  const [year, setYear] = useState<number>(new Date().getFullYear());

  const months = [
    { value: 1, label: 'January' },
    { value: 2, label: 'February' },
    { value: 3, label: 'March' },
    { value: 4, label: 'April' },
    { value: 5, label: 'May' },
    { value: 6, label: 'June' },
    { value: 7, label: 'July' },
    { value: 8, label: 'August' },
    { value: 9, label: 'September' },
    { value: 10, label: 'October' },
    { value: 11, label: 'November' },
    { value: 12, label: 'December' },
  ];

  const years = Array.from({ length: 6 }, (_, i) => new Date().getFullYear() - i);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!bankFile || !splitwiseFile) {
      alert('Please select both files');
      return;
    }

    onSubmit(bankFile, splitwiseFile, month, year);
  };

  const isFormValid = bankFile && splitwiseFile;

  return (
    <Card className="max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Upload Financial Data</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Bank Statement Upload */}
          <div className="space-y-2">
            <Label htmlFor="bank-file">Bank Statement (CSV)</Label>
            <Input
              id="bank-file"
              type="file"
              accept=".csv"
              onChange={(e) => setBankFile(e.target.files?.[0] || null)}
              disabled={loading}
            />
            {bankFile && (
              <p className="text-sm text-green-600">✓ {bankFile.name}</p>
            )}
          </div>

          {/* Splitwise Export Upload */}
          <div className="space-y-2">
            <Label htmlFor="splitwise-file">Splitwise Export (CSV)</Label>
            <Input
              id="splitwise-file"
              type="file"
              accept=".csv"
              onChange={(e) => setSplitWiseFile(e.target.files?.[0] || null)}
              disabled={loading}
            />
            {splitwiseFile && (
              <p className="text-sm text-green-600">✓ {splitwiseFile.name}</p>
            )}
          </div>

          {/* Month & Year Selection */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="month">Month</Label>
              <Select
                value={month.toString()}
                onValueChange={(val) => setMonth(parseInt(val))}
                disabled={loading}
              >
                <SelectTrigger id="month">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {months.map((m) => (
                    <SelectItem key={m.value} value={m.value.toString()}>
                      {m.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="year">Year</Label>
              <Select
                value={year.toString()}
                onValueChange={(val) => setYear(parseInt(val))}
                disabled={loading}
              >
                <SelectTrigger id="year">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {years.map((y) => (
                    <SelectItem key={y} value={y.toString()}>
                      {y}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            disabled={!isFormValid || loading}
          >
            {loading ? 'Processing...' : 'Upload & Analyze'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}