import React from 'react';

export interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = '' }) => {
  return (
    <div
      className={`animate-pulse bg-surface-secondary/80 rounded-md ${className}`}
      aria-hidden="true"
    />
  );
};

export interface LoadingSkeletonProps {
  height?: string;
  width?: string;
  className?: string;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  height = 'h-4',
  width = 'w-full',
  className = '',
}) => {
  return <Skeleton className={`${height} ${width} ${className}`} />;
};

export const MetricCardSkeleton: React.FC = () => {
  return (
    <div className="bg-surface border border-border-theme rounded-xl p-5 space-y-3">
      <div className="flex justify-between items-center">
        <Skeleton className="h-3.5 w-24" />
        <Skeleton className="h-5 w-5 rounded-md" />
      </div>
      <Skeleton className="h-7 w-32" />
      <div className="flex items-center gap-2 pt-1">
        <Skeleton className="h-4 w-12" />
        <Skeleton className="h-3 w-28" />
      </div>
    </div>
  );
};

export const TableRowSkeleton: React.FC<{ columns?: number }> = ({ columns = 5 }) => {
  return (
    <div className="flex items-center justify-between py-3.5 px-4 border-b border-border-subtle">
      {Array.from({ length: columns }).map((_, i) => (
        <Skeleton
          key={i}
          className={`h-4 ${i === 0 ? 'w-28' : i === columns - 1 ? 'w-16' : 'w-20'}`}
        />
      ))}
    </div>
  );
};

export const CardSkeleton: React.FC<{ lines?: number }> = ({ lines = 3 }) => {
  return (
    <div className="bg-surface border border-border-theme rounded-xl p-6 space-y-4">
      <Skeleton className="h-5 w-40" />
      <div className="space-y-2.5">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton
            key={i}
            className={`h-4 ${i === lines - 1 ? 'w-3/4' : 'w-full'}`}
          />
        ))}
      </div>
    </div>
  );
};
