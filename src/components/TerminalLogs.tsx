import React, { useEffect, useRef, useState } from 'react';
import { Terminal, Copy, Check, ChevronDown, ChevronUp, Download } from 'lucide-react';

interface TerminalLogsProps {
  logs?: string[];
  activeSubtask?: string;
  isStreaming?: boolean;
}

export const TerminalLogs: React.FC<TerminalLogsProps> = ({ 
  logs = [], 
  activeSubtask,
  isStreaming = false 
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);

  // Auto scroll to bottom when new logs arrive
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleCopyLogs = () => {
    navigator.clipboard.writeText(logs.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-lg border border-[#232A35] bg-[#0B0D10] overflow-hidden">
      {/* Console Titlebar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-[#14171D] border-b border-[#232A35]">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 mr-2">
            <div className="w-2.5 h-2.5 rounded-full bg-[#FF5C5C]/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#F5A623]/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#37E2C4]/60" />
          </div>
          <Terminal className="w-3.5 h-3.5 text-[#F5A623]" />
          <span className="font-mono text-xs font-bold tracking-wider uppercase text-[#F2F1ED]">
            SANDBOX EXECUTION LOGS
          </span>
          {isStreaming && (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono bg-[#F5A623]/15 text-[#F5A623] border border-[#F5A623]/30">
              <span className="w-1.5 h-1.5 rounded-full bg-[#F5A623] animate-ping" />
              LIVE STREAM
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {activeSubtask && (
            <span className="hidden sm:inline-block text-[11px] font-mono text-[#8E96A0] px-2 py-0.5 rounded bg-[#1C222B]">
              {activeSubtask}
            </span>
          )}
          <button
            onClick={handleCopyLogs}
            className="p-1 rounded text-[#8E96A0] hover:text-[#F2F1ED] transition-colors cursor-pointer"
            title="Copy logs"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-[#37E2C4]" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 rounded text-[#8E96A0] hover:text-[#F2F1ED] transition-colors cursor-pointer"
          >
            {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Terminal View */}
      {isExpanded && (
        <div 
          ref={containerRef}
          className="p-4 font-mono text-xs text-[#8E96A0] h-64 overflow-y-auto space-y-1.5 selection:bg-[#F5A623]/30 selection:text-[#F5A623]"
        >
          {logs.length === 0 ? (
            <div className="text-[#8E96A0] italic">Waiting for pipeline events...</div>
          ) : (
            logs.map((log, index) => {
              const isError = log.includes('FAIL') || log.includes('error') || log.includes('Flaw') || log.includes('Error');
              const isSuccess = log.includes('passed') || log.includes('PASSED') || log.includes('SEALED') || log.includes('VERIFIED');
              const isExtract = log.includes('[EXTRACT]') || log.includes('[ANALYZE]');
              const isAi = log.includes('[AI_VERIFY]');

              let colorClass = 'text-[#F2F1ED]';
              if (isError) colorClass = 'text-[#FF5C5C]';
              else if (isSuccess) colorClass = 'text-[#37E2C4]';
              else if (isExtract) colorClass = 'text-[#F5A623]';
              else if (isAi) colorClass = 'text-purple-300';

              return (
                <div key={index} className="flex items-start gap-2 leading-relaxed">
                  <span className="text-[#2A3038] select-none">{String(index + 1).padStart(2, '0')}</span>
                  <span className={colorClass}>
                    {log}
                  </span>
                </div>
              );
            })
          )}
          {isStreaming && (
            <div className="flex items-center gap-2 text-[#F5A623]">
              <span className="w-2 h-4 bg-[#F5A623] animate-pulse inline-block" />
            </div>
          )}
        </div>
      )}
    </div>
  );
};
