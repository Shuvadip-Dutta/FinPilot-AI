import React from 'react';
import { ProvenanceData, AgentExecutionStep } from '../../types/research';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import {
  GitCommit,
  Cpu,
  Clock,
  Layers,
  Wrench,
  CheckCircle2,
  Database,
  Hash,
  Activity,
} from 'lucide-react';

interface ProvenancePanelProps {
  provenance?: ProvenanceData;
  className?: string;
}

export const ProvenancePanel: React.FC<ProvenancePanelProps> = ({
  provenance,
  className = '',
}) => {
  if (!provenance) {
    return (
      <Card
        title={
          <div className="flex items-center gap-2">
            <GitCommit className="w-4 h-4 text-indigo-400" />
            <span>Agentic Provenance Trace</span>
          </div>
        }
        subtitle="Execution metadata and multi-agent workflow transparency"
        className={className}
      >
        <div className="py-8 text-center text-slate-400 text-xs flex flex-col items-center">
          <div className="w-10 h-10 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mb-2">
            <Cpu className="w-5 h-5" />
          </div>
          <p className="font-medium text-slate-300">No provenance trace recorded</p>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Agent traces, tool execution parameters, and model metadata will be logged here.
          </p>
        </div>
      </Card>
    );
  }

  // Normalize steps and agents
  const steps: AgentExecutionStep[] = Array.isArray(provenance.steps)
    ? provenance.steps
    : Array.isArray(provenance.agents) && typeof provenance.agents[0] === 'object'
    ? (provenance.agents as AgentExecutionStep[])
    : [];

  const agentNames: string[] = Array.isArray(provenance.agents)
    ? provenance.agents.map((a) => (typeof a === 'string' ? a : a.name || a.agent || 'Agent'))
    : [];

  return (
    <Card
      title={
        <div className="flex items-center gap-2">
          <GitCommit className="w-4 h-4 text-indigo-400" />
          <span>Agentic Provenance Trace</span>
          <Badge variant="info" size="sm">
            LangGraph
          </Badge>
        </div>
      }
      subtitle="Complete deterministic & LLM reasoning trace delivered by backend"
      className={className}
    >
      <div className="space-y-4 text-xs">
        {/* Top Overview Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <div className="flex items-center gap-1.5 text-slate-400 text-[10.5px] mb-1">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              <span>Model</span>
            </div>
            <p className="font-mono text-xs font-semibold text-slate-200 truncate">
              {provenance.model ? String(provenance.model) : 'Multi-Agent LLM'}
            </p>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <div className="flex items-center gap-1.5 text-slate-400 text-[10.5px] mb-1">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              <span>Latency</span>
            </div>
            <p className="font-mono text-xs font-semibold text-cyan-300">
              {provenance.execution_time_ms ? `${provenance.execution_time_ms} ms` : '—'}
            </p>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <div className="flex items-center gap-1.5 text-slate-400 text-[10.5px] mb-1">
              <Layers className="w-3.5 h-3.5 text-emerald-400" />
              <span>Agents Run</span>
            </div>
            <p className="font-mono text-xs font-semibold text-emerald-300">
              {agentNames.length > 0 ? agentNames.length : steps.length > 0 ? steps.length : '1+'}
            </p>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80">
            <div className="flex items-center gap-1.5 text-slate-400 text-[10.5px] mb-1">
              <Database className="w-3.5 h-3.5 text-amber-400" />
              <span>RAG Chunks</span>
            </div>
            <p className="font-mono text-xs font-semibold text-amber-300">
              {provenance.rag_documents_retrieved ?? '—'}
            </p>
          </div>
        </div>

        {/* Involved Agents list */}
        {agentNames.length > 0 && (
          <div>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono block mb-1.5">
              Participating Agents
            </span>
            <div className="flex flex-wrap gap-1.5">
              {agentNames.map((agent, i) => (
                <span
                  key={i}
                  className="px-2 py-1 rounded bg-slate-950 border border-slate-800 text-[11px] text-slate-300 font-mono flex items-center gap-1.5"
                >
                  <Activity className="w-3 h-3 text-cyan-400" />
                  {agent}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Execution Steps */}
        {steps.length > 0 && (
          <div className="space-y-2">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono block">
              Node Execution Details
            </span>

            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {steps.map((step, idx) => {
                const stepName = step.name || step.agent || `Step ${idx + 1}`;
                const duration = step.duration_ms ?? step.latency_ms;
                const tools = Array.isArray(step.tools_called) ? step.tools_called : [];

                return (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="font-semibold text-slate-200 font-mono">
                          {stepName}
                        </span>
                      </div>
                      {duration !== undefined && (
                        <span className="text-[10px] font-mono text-slate-500">
                          {duration}ms
                        </span>
                      )}
                    </div>

                    {step.summary && (
                      <p className="text-slate-400 text-[11px] leading-relaxed">
                        {step.summary}
                      </p>
                    )}

                    {tools.length > 0 && (
                      <div className="pt-1 flex items-center gap-1 flex-wrap">
                        <span className="text-[10px] text-slate-500 font-mono flex items-center gap-1">
                          <Wrench className="w-2.5 h-2.5 text-cyan-400" />
                          Tools:
                        </span>
                        {tools.map((tool, tIdx) => {
                          const toolName = typeof tool === 'string' ? tool : tool.tool;
                          return (
                            <span
                              key={tIdx}
                              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-cyan-300"
                            >
                              {toolName}
                            </span>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Workflow Raw Signature */}
        {provenance.workflow && (
          <div className="p-2.5 rounded bg-slate-950/80 border border-slate-900 text-[11px] font-mono text-slate-500 flex items-center justify-between">
            <span className="text-slate-400">Workflow Graph:</span>
            <span className="text-cyan-400">{String(provenance.workflow)}</span>
          </div>
        )}
      </div>
    </Card>
  );
};
