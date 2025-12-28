'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { X } from 'lucide-react';

interface Transaction {
  date: string;
  description: string;
  amount: number;
  category: string;
  source: string;
}

interface TransactionModalProps {
  open: boolean;
  onClose: () => void;
  transactions: Transaction[];
}

export function TransactionModal({ open, onClose, transactions }: TransactionModalProps) {
  const formatCurrency = (amount: number) => {
    return Math.abs(amount).toLocaleString('en-IN', { maximumFractionDigits: 0 });
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Transaction Details ({transactions.length})</DialogTitle>
        </DialogHeader>

        <div className="overflow-y-auto flex-1">
          <table className="w-full">
            <thead className="bg-gray-50 sticky top-0">
              <tr className="border-b">
                <th className="text-left p-3 text-sm font-semibold">Date</th>
                <th className="text-left p-3 text-sm font-semibold">Description</th>
                <th className="text-right p-3 text-sm font-semibold">Amount</th>
                <th className="text-left p-3 text-sm font-semibold">Category</th>
                <th className="text-left p-3 text-sm font-semibold">Source</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((txn, idx) => (
                <tr key={idx} className="border-b hover:bg-gray-50 transition-colors">
                  <td className="p-3 text-sm whitespace-nowrap">{formatDate(txn.date)}</td>
                  <td className="p-3 text-sm">{txn.description}</td>
                  <td className="p-3 text-sm text-right font-semibold text-red-600">
                    ₹{formatCurrency(txn.amount)}
                  </td>
                  <td className="p-3 text-sm">
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                      {txn.category}
                    </span>
                  </td>
                  <td className="p-3 text-sm">
                    <span className={`px-2 py-1 rounded text-xs ${
                      txn.source === 'BANK' 
                        ? 'bg-purple-100 text-purple-800' 
                        : 'bg-orange-100 text-orange-800'
                    }`}>
                      {txn.source}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </DialogContent>
    </Dialog>
  );
}