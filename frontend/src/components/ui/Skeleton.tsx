import React from 'react';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'line' | 'circle' | 'block';
}

export function Skeleton({ variant = 'line', className = '', ...rest }: SkeletonProps) {
  const shapeClass =
    variant === 'circle'
      ? 'rounded-full h-10 w-10'
      : variant === 'block'
        ? 'rounded-card h-24 w-full'
        : 'rounded-lg h-4 w-full';

  return (
    <div
      aria-busy="true"
      aria-live="polite"
      className={`animate-pulse bg-brand-200/60 ${shapeClass} ${className}`}
      {...rest}
    />
  );
}
