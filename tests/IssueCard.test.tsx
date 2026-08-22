import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { IssueCard } from '../src/components/IssueCard';
import { VerificationIssue } from '../src/lib/types';

describe('IssueCard Component', () => {
  const mockIssue: VerificationIssue = {
    id: 'ISSUE-01',
    category: 'requirement_violation',
    severity: 'critical',
    title: 'Session Revocation Does Not Cascade to Child Sessions',
    file: 'src/services/sessionManager.ts',
    line: 142,
    code_snippet: 'await db.refreshToken.update({ where: { id: tokenId } });',
    evidence: 'PR requirement REQ-03 explicitly dictates revocation of child tokens.',
    why_it_matters: 'Enables unauthorized session reuse after user logout.',
    suggested_fix: 'await redis.setex(`blacklist:${tokenId}`, 3600, "revoked");'
  };

  it('renders issue what, where, evidence, why it matters, and suggested fix', () => {
    render(<IssueCard issue={mockIssue} defaultExpanded={true} />);

    // What failed
    expect(screen.getByText('Session Revocation Does Not Cascade to Child Sessions')).toBeInTheDocument();
    expect(screen.getByText('critical')).toBeInTheDocument();
    expect(screen.getByText('requirement violation')).toBeInTheDocument();

    // Where
    expect(screen.getAllByText('src/services/sessionManager.ts').length).toBeGreaterThan(0);
    expect(screen.getAllByText(':142').length).toBeGreaterThan(0);

    // Evidence
    expect(screen.getByText(/PR requirement REQ-03 explicitly dictates/i)).toBeInTheDocument();

    // Why it matters
    expect(screen.getByText(/Enables unauthorized session reuse/i)).toBeInTheDocument();

    // Suggested Fix
    expect(screen.getByText(/await redis.setex/i)).toBeInTheDocument();
  });

  it('handles copy button interaction', async () => {
    render(<IssueCard issue={mockIssue} defaultExpanded={true} />);
    const copyButton = screen.getByRole('button', { name: /copy patch/i });
    expect(copyButton).toBeInTheDocument();

    fireEvent.click(copyButton);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockIssue.suggested_fix);
  });
});
