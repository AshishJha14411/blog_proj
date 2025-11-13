import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'

// This ensures your test DOM is cleaned up after each test
afterEach(() => {
  cleanup()
})

import '@testing-library/jest-dom/vitest'

// --- THIS IS THE FIX ---

// 1. Create a fake in-memory storage
const createMockStorage = () => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
};

// 2. Attach the mock storage to the 'window' object
Object.defineProperty(window, 'localStorage', {
  value: createMockStorage(),
});
Object.defineProperty(window, 'sessionStorage', {
  value: createMockStorage(),
});

// --- END FIX ---

// This ensures your test DOM is cleaned up after each test
afterEach(() => {
  cleanup()
})