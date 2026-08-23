import React from 'react';
import { CheckCircle2, XCircle, FlaskConical, Shield, Bot, FileCheck, ArrowUpRight } from 'lucide-react';
import { VerifyResult } from '../lib/types';

interface SummaryGridProps {
  summary: VerifyResult['summary'];
}

export const SummaryGrid: React.FC<SummaryGridProps> = ({ summary }) => {
  const cards = [
    {
      id: 'tests',
      title: 'TEST SUITE',
      label: 'Synthesized & Dynamic Tests',
      icon: FlaskConical,
      status: summary.tests.status,
      metric: `${summary.tests.passed} / ${summary.tests.total} PASSED`,
      detail: summary.tests.status === 'PASS' ? 'All dynamic unit, fuzz, & property suites green' : `${summary.tests.total - summary.tests.passed} failing test cases in sandbox`,
    },
    {
      id: 'security',
      title: 'SECURITY & AST',
      label: 'Static Analysis & Vulnerability Guard',
      icon: Shield,
      status: summary.security.status,
      metric: summary.security.issue_count === 0 ? '0 VULNERABILITIES' : `${summary.security.issue_count} ISSUES FLAGGED`,
      detail: summary.security.issue_count === 0 ? 'No timing attacks, injections, or IDORs detected' : 'Security invariants failed boundary checks',
    },
    {
      id: 'ai_check',
      title: 'AI ADVERSARIAL CHECK',
      label: 'Semantic Equivalence & Invariants',
      icon: Bot,
      status: summary.ai_check.status,
      metric: summary.ai_check.status === 'PASS' ? 'ADVERSARIAL PASS' : 'ADVERSARIAL FLAW',
      detail: summary.ai_check.status === 'PASS' ? 'Zero edge-case breakages under synthetic attacks' : 'Adversarial prompt/race vectors triggered flaws',
    },
    {
      id: 'requirements',
      title: 'REQUIREMENTS PROVER',
      label: 'PR Specification Invariants',
      icon: FileCheck,
      status: summary.requirements.status,
      metric: summary.requirements.status === 'PASS' ? '100% COMPLIANT' : 'CONTRACT BREACH',
      detail: summary.requirements.status === 'PASS' ? 'All extracted specifications mathematically proved' : 'Violates declared PR invariants & behavioral rules',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="summary-grid">
      {cards.map((card) => {
        const isPass = card.status === 'PASS';
        const Icon = card.icon;

        return (
          <div
            key={card.id}
            className={`relative rounded-md border p-4 bg-[#14171D] transition-all hover:bg-[#1C222B] ${
              isPass ? 'border-[#2A3038] hover:border-[#37E2C4]/40' : 'border-[#FF5C5C]/40 bg-[#FF5C5C]/5'
            }`}
            data-testid={`summary-card-${card.id}`}
          >
            {/* Top Indicator */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className={`p-1.5 rounded ${isPass ? 'bg-[#37E2C4]/10 text-[#37E2C4]' : 'bg-[#FF5C5C]/10 text-[#FF5C5C]'}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#8E96A0]">
                  {card.title}
                </span>
              </div>
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold tracking-wide ${
                  isPass
                    ? 'bg-[#37E2C4]/15 text-[#37E2C4] border border-[#37E2C4]/30'
                    : 'bg-[#FF5C5C]/15 text-[#FF5C5C] border border-[#FF5C5C]/30'
                }`}
                data-testid={`status-badge-${card.id}`}
              >
                {isPass ? (
                  <>
                    <CheckCircle2 className="w-3 h-3" />
                    PASS
                  </>
                ) : (
                  <>
                    <XCircle className="w-3 h-3" />
                    FAIL
                  </>
                )}
              </span>
            </div>

            {/* Metric & Detail */}
            <div className="space-y-1">
              <div className={`font-mono text-sm font-bold ${isPass ? 'text-[#F2F1ED]' : 'text-[#FF5C5C]'}`}>
                {card.metric}
              </div>
              <p className="text-xs text-[#8E96A0] line-clamp-2 leading-relaxed">
                {card.detail}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
