import { useEffect, useState } from 'react';
import { Badge, Button, Icon, Modal, Select } from '../../../components/ui';
import type {
  ExportFormat,
  ExportQuotaDto,
  ExportReceiptDto,
  ExportScope,
} from '../../../dtos/export.dto';
import { exportService, type IExportService } from '../../../services/export.service';

export interface ExportModalProps {
  defaultEntity?: ExportScope;
  service?: IExportService;
}

export function ExportModal({ defaultEntity = 'clusters', service = exportService }: ExportModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [scope, setScope] = useState<ExportScope>(defaultEntity);
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [quota, setQuota] = useState<ExportQuotaDto | null>(null);
  const [result, setResult] = useState<ExportReceiptDto | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    let isMounted = true;
    service.getQuota().then((q) => {
      if (isMounted) setQuota(q);
    });
    return () => {
      isMounted = false;
    };
  }, [isOpen, service]);

  const handleExport = async () => {
    setIsExporting(true);
    setError(null);
    try {
      const exportResult = await service.triggerExport(scope, format);
      const updatedQuota = await service.getQuota();
      setResult(exportResult);
      setQuota(updatedQuota);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to generate export.');
    } finally {
      setIsExporting(false);
    }
  };

  const isNewAccount = quota?.accountTier === 'new_account';

  return (
    <>
      <Button
        variant="secondary"
        size="sm"
        leftIcon="download"
        onClick={() => {
          setResult(null);
          setError(null);
          setIsOpen(true);
        }}
      >
        Export Data
      </Button>

      <Modal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Export Coordination Dataset"
        subtitle="Download cluster and channel intelligence in CSV or JSON format"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setIsOpen(false)}>
              Close
            </Button>
            <Button
              variant="primary"
              size="sm"
              leftIcon="download"
              isLoading={isExporting}
              onClick={() => void handleExport()}
            >
              Generate {format.toUpperCase()} Export
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          {quota ? (
            <div className="rounded-xl border border-brand-200 bg-brand-50/70 p-3.5 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-bold text-ink-primary">
                  <Icon name="shield-halved" className="mr-1.5 text-brand-500" />
                  Account Export Quota (NFR-10)
                </span>
                <Badge variant={isNewAccount ? 'medium' : 'success'}>
                  {isNewAccount ? 'New Account Cap (<7d)' : 'Verified Researcher'}
                </Badge>
              </div>
              <p className="mt-1.5 text-ink-secondary">
                Max rows per export:{' '}
                <strong className="font-bold text-ink-primary">{quota.maxRowsPerExport} rows</strong>{' '}
                • Daily exports remaining:{' '}
                <strong className="font-bold text-ink-primary">
                  {Math.max(0, quota.dailyExportsLimit - quota.dailyExportsUsed)} /{' '}
                  {quota.dailyExportsLimit}
                </strong>
              </p>
            </div>
          ) : null}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Select
              label="Dataset Entity"
              value={scope}
              onChange={(e) => setScope(e.target.value as ExportScope)}
              options={[
                { value: 'clusters', label: 'Coordinated Clusters' },
                { value: 'channels', label: 'Monitored Channels & Risk Scores' },
              ]}
            />
            <Select
              label="Output Format"
              value={format}
              onChange={(e) => setFormat(e.target.value as ExportFormat)}
              options={[
                { value: 'csv', label: 'CSV (Spreadsheet)' },
                { value: 'json', label: 'JSON (Structured + Explanations)' },
              ]}
            />
          </div>

          {error ? (
            <div
              role="alert"
              className="rounded-xl border border-status-danger/30 bg-status-dangerBg p-3 text-xs font-semibold text-status-dangerText"
            >
              <Icon name="triangle-exclamation" className="mr-1.5" />
              {error}
            </div>
          ) : null}

          {result ? (
            <div
              aria-label="Export confirmation receipt"
              className="rounded-xl border border-status-successBg bg-status-successBg p-3.5 text-xs text-ink-primary"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-status-successText">
                  <Icon name="circle-check" className="mr-1.5" />
                  Export Ready: {result.fileName}
                </span>
                <Badge variant="neutral">{result.rowsExported} rows</Badge>
              </div>
              <p className="mt-1 text-[11px] text-ink-muted">
                Generated at {result.generatedAt} ({result.format.toUpperCase()} • {result.scope})
              </p>
            </div>
          ) : null}
        </div>
      </Modal>
    </>
  );
}
