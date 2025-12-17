// app/upload/page.tsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { storage } from '@/lib/storage';
import { UploadForm } from '@/components/UploadForm';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

type UploadStatus = 'idle' | 'uploading' | 'processing' | 'completed' | 'error';

export default function UploadPage() {
  const router = useRouter();
  const [status, setStatus] = useState<UploadStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [progress, setProgress] = useState({
    bank_processed: 0,
    splitwise_processed: 0,
    total_transactions: 0,
    linked_pairs: 0,
    settlements: 0,
  });

  const handleUpload = async (
    bankFile: File,
    splitwiseFile: File,
    month: number,
    year: number
  ) => {
    try {
      setStatus('uploading');
      setError(null);

      // Upload files
      const response = await api.uploadFiles(bankFile, splitwiseFile, month, year);
      
      setSessionId(response.session_id);
      storage.setSessionId(response.session_id);
      
      setStatus('processing');

      // Poll for status
      pollStatus(response.session_id);
    } catch (err) {
      setStatus('error');
      setError(err instanceof Error ? err.message : 'Upload failed');
      console.error('Upload error:', err);
    }
  };

  const pollStatus = async (sessionId: string) => {
    const maxAttempts = 60; // 60 attempts = 2 minutes max
    let attempts = 0;

    const poll = async () => {
      try {
        attempts++;
        
        const statusData = await api.getSessionStatus(sessionId);
        
        setProgress(statusData.progress);

        if (statusData.status === 'completed') {
          setStatus('completed');
          setTimeout(() => {
            router.push('/dashboard');
          }, 1500);
          return;
        }

        if (statusData.status === 'failed') {
          setStatus('error');
          setError(statusData.error_message || 'Analysis failed');
          return;
        }

        // Continue polling if still processing
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000); // Poll every 2 seconds
        } else {
          setStatus('error');
          setError('Analysis timed out. Please try again.');
        }
      } catch (err) {
        console.error('Status poll error:', err);
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000);
        } else {
          setStatus('error');
          setError('Failed to check analysis status');
        }
      }
    };

    poll();
  };

  return (
    <div className="min-h-screen p-8 flex items-center justify-center">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">
            Financial Analysis Tool
          </h1>
          <p className="text-gray-600 mt-2">
            Upload your bank statement and Splitwise export to get started
          </p>
        </div>

        {/* Upload Form */}
        {status === 'idle' && (
          <UploadForm onSubmit={handleUpload} loading={false} />
        )}

        {/* Uploading State */}
        {status === 'uploading' && (
          <Card className="max-w-2xl mx-auto">
            <CardHeader>
              <CardTitle>Uploading Files...</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
              <p className="text-center text-gray-600">
                Please wait while we upload your files
              </p>
            </CardContent>
          </Card>
        )}

        {/* Processing State */}
        {status === 'processing' && (
          <Card className="max-w-2xl mx-auto">
            <CardHeader>
              <CardTitle>Analyzing Your Data...</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-center py-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              </div>
              
              <div className="space-y-2 text-sm text-gray-600">
                <p>✓ Bank transactions: {progress.bank_processed}</p>
                <p>✓ Splitwise transactions: {progress.splitwise_processed}</p>
                <p>✓ Total processed: {progress.total_transactions}</p>
                <p>✓ Linked pairs: {progress.linked_pairs}</p>
                <p>✓ Settlements detected: {progress.settlements}</p>
              </div>

              <p className="text-center text-gray-500 pt-4">
                This may take 10-30 seconds...
              </p>
            </CardContent>
          </Card>
        )}

        {/* Completed State */}
        {status === 'completed' && (
          <Card className="max-w-2xl mx-auto border-green-200 bg-green-50">
            <CardHeader>
              <CardTitle className="text-green-800">✓ Analysis Complete!</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-green-700 text-center">
                Redirecting to dashboard...
              </p>
            </CardContent>
          </Card>
        )}

        {/* Error State */}
        {status === 'error' && (
          <Card className="max-w-2xl mx-auto border-red-200 bg-red-50">
            <CardHeader>
              <CardTitle className="text-red-800">Error</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-red-700 mb-4">{error}</p>
              <button
                onClick={() => {
                  setStatus('idle');
                  setError(null);
                }}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Try Again
              </button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}