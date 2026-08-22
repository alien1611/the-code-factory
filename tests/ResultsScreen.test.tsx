import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ResultsScreen } from '../src/screens/ResultsScreen';

describe('ResultsScreen Component', () => {
  it('renders verified results and passed test list for happy path', async () => {
    render(
      <MemoryRouter initialEntries={['/results/job-vfy-142-pass']}>
        <Routes>
          <Route path="/results/:jobId" element={<ResultsScreen forcedScenario="verified" />} />
        </Routes>
      </MemoryRouter>
    );

    // Should load and display VERIFIED
    await waitFor(() => {
      expect(screen.getByTestId('verdict-title')).toHaveTextContent('VERIFIED');
    });

    // Check summary cards
    expect(screen.getByTestId('summary-card-tests')).toHaveTextContent('18 / 18 PASSED');
    expect(screen.getByTestId('summary-card-security')).toHaveTextContent('0 VULNERABILITIES');

    // Requirements checklist
    expect(screen.getByTestId('requirements-checklist')).toBeInTheDocument();
  });

  it('renders violation results with issues list for failing PRs', async () => {
    render(
      <MemoryRouter initialEntries={['/results/job-vfy-89-fail']}>
        <Routes>
          <Route path="/results/:jobId" element={<ResultsScreen forcedScenario="violation" />} />
        </Routes>
      </MemoryRouter>
    );

    // Should load and display REQUIREMENT VIOLATION
    await waitFor(() => {
      expect(screen.getByTestId('verdict-title')).toHaveTextContent('REQUIREMENT VIOLATION');
    });

    // Check summary failure indicators
    expect(screen.getByTestId('summary-card-tests')).toHaveTextContent('14 / 17 PASSED');
    expect(screen.getByTestId('summary-card-security')).toHaveTextContent('3 ISSUES FLAGGED');

    // Issues list rendered
    expect(screen.getByTestId('issues-container')).toBeInTheDocument();
    expect(screen.getByText('Session Revocation Does Not Cascade to Child Sessions')).toBeInTheDocument();
  });

  it('allows toggling scenarios dynamically via the demo toolbar', async () => {
    const onSwitch = vi.fn();
    render(
      <MemoryRouter initialEntries={['/results/test-job']}>
        <Routes>
          <Route 
            path="/results/:jobId" 
            element={<ResultsScreen forcedScenario="violation" onSwitchScenario={onSwitch} />} 
          />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('verdict-title')).toHaveTextContent('REQUIREMENT VIOLATION');
    });

    const toggleVerifiedBtn = screen.getByTestId('toggle-verified-scenario');
    fireEvent.click(toggleVerifiedBtn);

    expect(onSwitch).toHaveBeenCalledWith('verified');
  });
});
