// lib/storage.ts

const SESSION_KEY = 'current_session_id';

export const storage = {
  setSessionId: (sessionId: string): void => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(SESSION_KEY, sessionId);
    }
  },

  getSessionId: (): string | null => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(SESSION_KEY);
    }
    return null;
  },

  clearSessionId: (): void => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(SESSION_KEY);
    }
  },
};