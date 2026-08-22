import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { SummaryGrid } from '../src/components/SummaryGrid';

describe('SummaryGrid Component', () => {
  it('renders all 4 summary cards with PASS status', () => {
    const passedSummary = {
      tests: { status: 'PASS' as const, passed: 18, total: 18 },
      security: { status: 'PASS' as const, issue_count: 0 },
      ai_check: { status: 'PASS' as const },
      requirements: { status: 'PASS' as const },
    };

    render(<SummaryGrid summary={passedSummary} />);

    expect(screen.getByTestId('summary-card-tests')).toBeInTheDocument();
    expect(screen.getByTestId('summary-card-security')).toBeInTheDocument();
    expect(screen.getByTestId('summary-card-ai_check')).toBeInTheDocument();
    expect(screen.getByTestId('summary-card-requirements')).toBeInTheDocument();

    expect(screen.getByText('18 / 18 PASSED')).toBeInTheDocument();
    expect(screen.getByText('0 VULNERABILITIES')).toBeInTheDocument();
    expect(screen.getByText('ADVERSARIAL PASS')).toBeInTheDocument();
    expect(screen.getByText('100% COMPLIANT')).toBeInTheDocument();
  });

  it('renders FAIL statuses when violations occur', () => {
    const failedSummary = {
      tests: { status: 'FAIL' as const, passed: 14, total: 17 },
      security: { status: 'FAIL' as const, issue_count: 3 },
      ai_check: { status: 'FAIL' as const },
      requirements: { status: 'FAIL' as const },
    };

    render(<SummaryGrid summary={failedSummary} />);

    expect(screen.getByText('14 / 17 PASSED')).toBeInTheDocument();
    expect(screen.getByText('3 ISSUES FLAGGED')).toBeInTheDocument();
    expect(screen.getByText('ADVERSARIAL FLAW')).toBeInTheDocument();
    expect(screen.getByText('CONTRACT BREACH')).toBeInTheDocument();
  });
});
