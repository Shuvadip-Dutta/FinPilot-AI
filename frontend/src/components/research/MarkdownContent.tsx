import React from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export const MarkdownContent: React.FC<MarkdownContentProps> = ({ content, className = '' }) => {
  return (
    <div className={`markdown-body text-text-primary text-sm leading-relaxed ${className}`}>
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-xl font-bold text-text-primary mt-5 mb-3 border-b border-border-theme pb-2">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-semibold text-accent-primary mt-4 mb-2 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-primary" />
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-medium text-text-primary mt-3 mb-1.5">
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p className="mb-3 text-text-secondary leading-relaxed last:mb-0">
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-outside ml-5 mb-3 space-y-1 text-text-secondary">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-outside ml-5 mb-3 space-y-1 text-text-secondary">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-text-secondary leading-normal pl-1">
              {children}
            </li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-accent-primary pl-3 py-1 my-3 bg-accent-soft/40 rounded-r text-text-secondary italic">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto my-4 rounded-lg border border-border-theme bg-surface-secondary/40">
              <table className="w-full text-xs text-left border-collapse">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-surface-secondary text-text-secondary uppercase tracking-wider font-mono text-[11px] border-b border-border-theme">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-border-theme font-mono text-[12px]">
              {children}
            </tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-surface-secondary/60 transition-colors">
              {children}
            </tr>
          ),
          th: ({ children }) => (
            <th className="px-3.5 py-2.5 font-semibold text-text-primary">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3.5 py-2 text-text-secondary whitespace-nowrap">
              {children}
            </td>
          ),
          code: ({ children, className }) => {
            const isInline = !className;
            return isInline ? (
              <code className="px-1.5 py-0.5 rounded bg-surface-secondary text-accent-primary font-mono text-xs border border-border-theme">
                {children}
              </code>
            ) : (
              <div className="my-3 rounded-lg overflow-hidden border border-border-theme bg-surface-secondary/80 p-3 font-mono text-xs text-text-primary overflow-x-auto">
                <code>{children}</code>
              </div>
            );
          },
          strong: ({ children }) => (
            <strong className="font-semibold text-text-primary">
              {children}
            </strong>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent-primary hover:text-accent-hover underline underline-offset-2 transition-colors"
            >
              {children}
            </a>
          ),
        }}
      >
        {content}
      </Markdown>
    </div>
  );
};
