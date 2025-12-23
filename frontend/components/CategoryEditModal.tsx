// components/CategoryEditModal.tsx

'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { api } from '@/lib/api';
import { storage } from '@/lib/storage';
import { Transaction } from '@/types';
import { Loader2 } from 'lucide-react';

interface CategoryEditModalProps {
  transaction: Transaction;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function CategoryEditModal({
  transaction,
  open,
  onClose,
  onSuccess,
}: CategoryEditModalProps) {
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>(
    transaction.category || 'Other'
  );
  const [applyToSimilar, setApplyToSimilar] = useState(false);
  const [createRule, setCreateRule] = useState(false);
  const [similarCount, setSimilarCount] = useState<number>(0);
  const [pattern, setPattern] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      fetchCategories();
      fetchSimilarCount();
    }
  }, [open]);

  const fetchCategories = async () => {
    try {
      const data = await api.getCategories();
      setCategories(data.categories);
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    }
  };

  const fetchSimilarCount = async () => {
    const sessionId = storage.getSessionId();
    if (!sessionId) return;

    try {
      setLoadingPreview(true);
      const data = await api.getSimilarCount(sessionId, transaction.id, transaction.source);
      setSimilarCount(data.count);
      setPattern(data.pattern);
      
      // Auto-check "apply to similar" if count > 0 and confidence is reasonable
      if (data.count > 0) {
        setApplyToSimilar(true);
        setCreateRule(true);
      }
    } catch (err) {
      console.error('Failed to fetch similar count:', err);
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleSave = async () => {
    const sessionId = storage.getSessionId();
    if (!sessionId) return;

    try {
      setLoading(true);
      setError(null);

      const result = await api.updateTransactionCategory(
        sessionId,
        transaction.id,
        transaction.source,
        selectedCategory,
        applyToSimilar,
        createRule
      );

      onSuccess();
      onClose();

      // Show success message with count
      console.log(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update category');
    } finally {
      setLoading(false);
    }
  };

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
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Change Category</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Transaction Info */}
          <div className="p-3 bg-gray-50 rounded-lg">
            <p className="font-medium text-gray-900">{transaction.description}</p>
            <p className="text-sm text-gray-600 mt-1">
              {formatDate(transaction.date)} • ₹{formatCurrency(transaction.amount)} • {transaction.source}
            </p>
          </div>

          {/* Current Category */}
          <div>
            <Label className="text-sm text-gray-600">Current Category</Label>
            <p className="font-medium text-gray-900 mt-1">
              {transaction.category || 'Uncategorized'}
            </p>
          </div>

          {/* New Category Selector */}
          <div className="space-y-2">
            <Label htmlFor="category">New Category</Label>
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger id="category">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {categories.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Similar Transactions Preview */}
          {loadingPreview ? (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Checking for similar transactions...</span>
            </div>
          ) : (
            pattern && (
              <div className="space-y-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-gray-700">
                  Pattern detected: <span className="font-semibold">{pattern}</span>
                </p>
                {similarCount > 0 && (
                  <p className="text-sm text-blue-700">
                    Found {similarCount} similar transaction{similarCount !== 1 ? 's' : ''}
                  </p>
                )}

                {/* Apply to Similar Checkbox */}
                {similarCount > 0 && (
                  <div className="flex items-start gap-2">
                    <Checkbox
                      id="apply-similar"
                      checked={applyToSimilar}
                      onCheckedChange={(checked) => setApplyToSimilar(checked as boolean)}
                    />
                    <div className="flex-1">
                      <label
                        htmlFor="apply-similar"
                        className="text-sm font-medium text-gray-900 cursor-pointer"
                      >
                        Apply to all {pattern} transactions
                      </label>
                      <p className="text-xs text-gray-600 mt-0.5">
                        This will update {similarCount + 1} transaction{similarCount + 1 !== 1 ? 's' : ''} in this
                        month
                      </p>
                    </div>
                  </div>
                )}

                {/* Save Rule Checkbox */}
                <div className="flex items-start gap-2">
                  <Checkbox
                    id="create-rule"
                    checked={createRule}
                    onCheckedChange={(checked) => setCreateRule(checked as boolean)}
                  />
                  <div className="flex-1">
                    <label
                      htmlFor="create-rule"
                      className="text-sm font-medium text-gray-900 cursor-pointer"
                    >
                      Save as rule for future uploads
                    </label>
                    <p className="text-xs text-gray-600 mt-0.5">
                      All future {pattern} transactions will be auto-categorized
                    </p>
                  </div>
                </div>
              </div>
            )
          )}

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <Button variant="outline" onClick={onClose} className="flex-1" disabled={loading}>
              Cancel
            </Button>
            <Button onClick={handleSave} className="flex-1" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}