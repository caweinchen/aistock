import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

describe('offline login state propagation', () => {
  it('passes offline login status from LoginScreen to App', () => {
    const loginScreen = readFileSync(resolve(__dirname, 'LoginScreen.tsx'), 'utf8');
    const app = readFileSync(resolve(__dirname, '../../App.tsx'), 'utf8');

    expect(loginScreen).toContain('onSuccess?: (state?: { isOffline?: boolean }) => void');
    expect(loginScreen).toContain('onSuccess({ isOffline: result.isOffline })');
    expect(app).toContain('const handleLoginSuccess = (state?: { isOffline?: boolean }) =>');
    expect(app).toContain('setIsOffline(state?.isOffline ?? false)');
  });
});
