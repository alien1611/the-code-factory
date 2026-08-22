import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProgressScreen } from '../src/screens/ProgressScreen';

describe('ProgressScreen Component', () => {
  it('renders progress screen with pipeline visualizer and sandbox terminal', async () => {
    render(
      <MemoryRouter initialEntries={['/verify/job-123']}>
        <Routes>
          <Route 
            path="/verify/:jobId" 
            element={
              <ProgressScreen 
                repoFullName="octocat/payment-gateway-service" 
                prNumber={142} 
              />
            } 
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/VERIFICATION IN PROGRESS/i)).toBeInTheDocument();
    expect(screen.getByText(/octocat\/payment-gateway-service #142/i)).toBeInTheDocument();
    expect(screen.getByTestId('current-step-label')).toBeInTheDocument();
    expect(screen.getByTestId('progress-pct')).toBeInTheDocument();
    expect(screen.getByText(/SANDBOX EXECUTION LOGS/i)).toBeInTheDocument();
  });
});
