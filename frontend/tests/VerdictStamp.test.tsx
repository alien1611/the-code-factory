import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { VerdictStamp } from '../src/components/VerdictStamp';

describe('VerdictStamp Component', () => {
  it('renders VERIFIED state correctly', () => {
    render(
      <VerdictStamp
        verdict="VERIFIED"
        repoFullName="octocat/payment-gateway-service"
        prNumber={142}
        prTitle="Add idempotent Stripe webhook handler"
        commitHash="9a7e3b1c"
        branch="feat/idempotent-stripe-webhooks"
        durationSec={4.8}
      />
    );

    const title = screen.getByTestId('verdict-title');
    expect(title).toHaveTextContent('VERIFIED');
    expect(screen.getByText(/PASSED 100%/i)).toBeInTheDocument();
    expect(screen.getByText(/octocat\/payment-gateway-service/i)).toBeInTheDocument();
    expect(screen.getByText(/#142/i)).toBeInTheDocument();
    expect(screen.getByText(/9a7e3b1c/i)).toBeInTheDocument();
    expect(screen.getByText(/4.8s run/i)).toBeInTheDocument();
  });

  it('renders REQUIREMENT_VIOLATION state correctly', () => {
    render(
      <VerdictStamp
        verdict="REQUIREMENT_VIOLATION"
        repoFullName="acme-corp/auth-core"
        prNumber={89}
        prTitle="Implement token refresh endpoint"
        commitHash="3d8f14a9"
        branch="feat/token-refresh-scopes"
        durationSec={6.2}
      />
    );

    const title = screen.getByTestId('verdict-title');
    expect(title).toHaveTextContent('REQUIREMENT VIOLATION');
    expect(screen.getByText(/ACTION REQUIRED/i)).toBeInTheDocument();
    expect(screen.getByText(/acme-corp\/auth-core/i)).toBeInTheDocument();
    expect(screen.getByText(/#89/i)).toBeInTheDocument();
    expect(screen.getByText(/3d8f14a9/i)).toBeInTheDocument();
    expect(screen.getByText(/6.2s run/i)).toBeInTheDocument();
  });
});
