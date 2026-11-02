import React from 'react';

export interface TableColumn<TRow> {
  key: string;
  header: React.ReactNode;
  render: (row: TRow, index: number) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  className?: string;
}

export interface TableProps<TRow> {
  columns: readonly TableColumn<TRow>[];
  data: readonly TRow[];
  rowKey: (row: TRow, index: number) => string;
  emptyMessage?: string;
  className?: string;
}

const ALIGN_CLASS: Record<'left' | 'center' | 'right', string> = {
  left: 'text-left',
  center: 'text-center',
  right: 'text-right',
};

export function Table<TRow>({
  columns,
  data,
  rowKey,
  emptyMessage = 'No records available.',
  className = '',
}: TableProps<TRow>) {
  return (
    <div className={`w-full overflow-x-auto rounded-card bg-surface-card shadow-card ${className}`}>
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-brand-100 bg-surface-muted/60">
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={`px-4 py-3.5 text-xs font-bold uppercase tracking-wider text-ink-muted ${
                  ALIGN_CLASS[col.align ?? 'left']
                } ${col.className ?? ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-brand-100/70">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-sm text-ink-muted">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => (
              <tr
                key={rowKey(row, rowIndex)}
                className="transition-colors hover:bg-surface-muted/50"
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`px-4 py-3.5 text-ink-secondary ${
                      ALIGN_CLASS[col.align ?? 'left']
                    } ${col.className ?? ''}`}
                  >
                    {col.render(row, rowIndex)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
