import React, { useState } from 'react';
import { CheckCircle2, XCircle, ChevronDown, ChevronUp, Clock, Filter, Sparkles, Shield, FlaskConical } from 'lucide-react';
import { TestCase } from '../lib/types';

interface TestListProps {
  tests: TestCase[];
  defaultExpanded?: boolean;
}

export const TestList: React.FC<TestListProps> = ({ 
  tests, 
  defaultExpanded = false 
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [filter, setFilter] = useState<'all' | 'pass' | 'fail'>('all');

  const filteredTests = tests.filter(t => {
    if (filter === 'pass') return t.status === 'pass';
    if (filter === 'fail') return t.status === 'fail';
    return true;
  });

  const passCount = tests.filter(t => t.status === 'pass').length;
  const failCount = tests.filter(t => t.status === 'fail').length;

  return (
    <div className="rounded-lg border border-[#2A3038] bg-[#14171D] overflow-hidden" data-testid="test-list-section">
      {/* Header */}
      <div 
        onClick={() => setIsExpanded(!isExpanded)}
        className="p-4 sm:p-5 flex items-center justify-between gap-4 cursor-pointer select-none bg-[#181C23] hover:bg-[#1C222B] transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-[#0B0D10] border border-[#2A3038]">
            <FlaskConical className="w-5 h-5 text-[#37E2C4]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-sans font-bold text-base sm:text-lg text-[#F2F1ED]">
                Dynamic & Adversarial Test Suite
              </h3>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#2A3038] text-[#8E96A0]">
                {tests.length} tests
              </span>
            </div>
            <p className="text-xs text-[#8E96A0] mt-0.5">
              {passCount} passed • {failCount} failed
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className={`px-2.5 py-1 rounded text-xs font-mono font-bold tracking-wide border ${
            failCount === 0 
              ? 'bg-[#37E2C4]/15 text-[#37E2C4] border-[#37E2C4]/30' 
              : 'bg-[#FF5C5C]/15 text-[#FF5C5C] border-[#FF5C5C]/30'
          }`}>
            {failCount === 0 ? 'ALL PASSED (100%)' : `${failCount} FAILED`}
          </span>
          <button 
            type="button"
            className="p-1 rounded text-[#8E96A0] hover:text-[#F2F1ED] transition-colors"
            aria-label={isExpanded ? "Collapse test list" : "Expand test list"}
          >
            {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-4 sm:p-6 border-t border-[#232A35] space-y-4">
          {/* Filter Toolbar */}
          <div className="flex items-center justify-between gap-2 border-b border-[#232A35] pb-3">
            <div className="flex items-center gap-1.5 font-mono text-xs text-[#8E96A0]">
              <Filter className="w-3.5 h-3.5" />
              <span>FILTER:</span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={(e) => { e.stopPropagation(); setFilter('all'); }}
                className={`px-2.5 py-1 text-xs font-mono rounded transition-colors cursor-pointer ${
                  filter === 'all' ? 'bg-[#2A3038] text-[#F2F1ED]' : 'text-[#8E96A0] hover:bg-[#1C222B]'
                }`}
              >
                All ({tests.length})
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); setFilter('pass'); }}
                className={`px-2.5 py-1 text-xs font-mono rounded transition-colors cursor-pointer ${
                  filter === 'pass' ? 'bg-[#37E2C4]/20 text-[#37E2C4]' : 'text-[#8E96A0] hover:bg-[#1C222B]'
                }`}
              >
                Passed ({passCount})
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); setFilter('fail'); }}
                className={`px-2.5 py-1 text-xs font-mono rounded transition-colors cursor-pointer ${
                  filter === 'fail' ? 'bg-[#FF5C5C]/20 text-[#FF5C5C]' : 'text-[#8E96A0] hover:bg-[#1C222B]'
                }`}
              >
                Failed ({failCount})
              </button>
            </div>
          </div>

          {/* Test items */}
          <div className="space-y-2">
            {filteredTests.map((test, idx) => {
              const isPass = test.status === 'pass';
              return (
                <div
                  key={idx}
                  className={`p-3 rounded-md border text-xs font-mono flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                    isPass 
                      ? 'bg-[#0B0D10] border-[#232A35]' 
                      : 'bg-[#FF5C5C]/5 border-[#FF5C5C]/30'
                  }`}
                  data-testid={`test-row-${test.name}`}
                >
                  <div className="flex items-start gap-2.5">
                    {isPass ? (
                      <CheckCircle2 className="w-4 h-4 text-[#37E2C4] mt-0.5 shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-[#FF5C5C] mt-0.5 shrink-0" />
                    )}
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`font-semibold ${isPass ? 'text-[#F2F1ED]' : 'text-[#FF5C5C]'}`}>
                          {test.name}
                        </span>
                        {test.category && (
                          <span className="px-1.5 py-0.2 rounded bg-[#2A3038] text-[#8E96A0] text-[10px] uppercase">
                            {test.category}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-[#8E96A0]">
                        {test.file}
                      </div>
                      {test.message && (
                        <p className={`text-[11px] font-sans ${isPass ? 'text-[#8E96A0]' : 'text-[#FF5C5C] font-mono mt-1'}`}>
                          {test.message}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center shrink-0 text-[#8E96A0]">
                    {test.duration_ms !== undefined && (
                      <span className="flex items-center gap-1 text-[11px]">
                        <Clock className="w-3 h-3 text-[#F5A623]" />
                        {test.duration_ms}ms
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
