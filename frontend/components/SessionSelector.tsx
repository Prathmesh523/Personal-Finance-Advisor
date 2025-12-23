'use client';

import { useSession } from '@/lib/session-context';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Calendar } from 'lucide-react';

export function SessionSelector() {
  const { sessions, currentSession, setCurrentSession, loading } = useSession();

  const formatMonth = (monthStr: string) => {
    const [year, month] = monthStr.split('-');
    const date = new Date(parseInt(year), parseInt(month) - 1);
    return date.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg animate-pulse">
        <Calendar className="w-5 h-5 text-gray-400" />
        <div className="w-32 h-5 bg-gray-200 rounded"></div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-2">
      <Calendar className="w-5 h-5 text-gray-600" />
      <Select value={currentSession || undefined} onValueChange={setCurrentSession}>
        <SelectTrigger className="w-[200px]">
          <SelectValue placeholder="Select month" />
        </SelectTrigger>
        <SelectContent>
          {sessions.map((session) => (
            <SelectItem key={session.id} value={session.id}>
              {formatMonth(session.month)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}