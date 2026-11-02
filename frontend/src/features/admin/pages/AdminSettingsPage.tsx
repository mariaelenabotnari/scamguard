import React, { useEffect, useState } from 'react';
import { AppShell } from '../../../components/layout';
import {
  Badge,
  Button,
  Card,
  Icon,
  Input,
  Skeleton,
} from '../../../components/ui';
import type { SystemParametersDto } from '../../../dtos/admin.dto';
import { adminService, type IAdminService } from '../../../services/admin.service';

export interface AdminSettingsPageProps {
  service?: IAdminService;
}

export function AdminSettingsPage({ service = adminService }: AdminSettingsPageProps) {
  const [params, setParams] = useState<SystemParametersDto | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [similarityInput, setSimilarityInput] = useState('0.82');
  const [timeWindowInput, setTimeWindowInput] = useState('30');
  const [collectionIntervalInput, setCollectionIntervalInput] = useState('5');
  const [minChannelsInput, setMinChannelsInput] = useState('3');
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let isMounted = true;
    service.getParameters().then((data) => {
      if (isMounted) {
        setParams(data);
        setSimilarityInput(String(data.similarityThreshold));
        setTimeWindowInput(String(data.timeWindowMinutes));
        setCollectionIntervalInput(String(data.collectionIntervalMinutes));
        setMinChannelsInput(String(data.minClusterChannels));
        setIsLoading(false);
      }
    });
    return () => {
      isMounted = false;
    };
  }, [service]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSaveMessage(null);
    setIsSaving(true);
    try {
      const updated = await service.updateParameters({
        similarityThreshold: Number(similarityInput),
        timeWindowMinutes: Number(timeWindowInput),
        collectionIntervalMinutes: Number(collectionIntervalInput),
        minClusterChannels: Number(minChannelsInput),
      });
      setParams(updated);
      setSaveMessage(
        `Saved new parameter version ${updated.parameterVersion}. Historical scores keep their original version tag (NFR-13).`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save parameters.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        <Card
          tone="banner"
          padding="lg"
          className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center"
        >
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">
              Threshold & System Settings
            </h1>
            <p className="mt-1 text-xs font-medium text-ink-muted">
              Versioned coordination parameters, cosine similarity thresholds, and collector polling
              intervals (NFR-01, NFR-13)
            </p>
          </div>
          {params ? (
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="brand" icon="sliders">
                Active Parameter Set: {params.parameterVersion}
              </Badge>
              <Badge variant="neutral" icon="clock">
                Max Poll: 10 min
              </Badge>
            </div>
          ) : null}
        </Card>

        {isLoading ? (
          <div aria-label="Loading admin parameters" className="space-y-3">
            <Skeleton variant="block" className="h-44 w-full" />
          </div>
        ) : (
          <Card>
            <form onSubmit={(e) => void handleSubmit(e)} className="space-y-5" noValidate>
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-brand-100 pb-3">
                <div>
                  <h2 className="text-sm font-bold text-ink-primary">
                    Detection & Collector Thresholds
                  </h2>
                  <p className="text-xs text-ink-muted">
                    Every change creates a new immutable parameter version so historical cluster
                    scores remain reproducible.
                  </p>
                </div>
                {params ? (
                  <span className="text-xs font-semibold text-ink-secondary">
                    Last updated by {params.updatedBy} at {params.updatedAt}
                  </span>
                ) : null}
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input
                  label="Cosine Similarity Threshold (0.50 – 0.99)"
                  type="number"
                  step="0.01"
                  value={similarityInput}
                  onChange={(e) => setSimilarityInput(e.target.value)}
                  hint="Minimum multilingual embedding cosine similarity to link two posts."
                />
                <Input
                  label="Coordination Time Window (minutes)"
                  type="number"
                  value={timeWindowInput}
                  onChange={(e) => setTimeWindowInput(e.target.value)}
                  hint="Maximum time delta M (minutes) between posts in a single cluster."
                />
                <Input
                  label="Collector Poll Interval (minutes, max 10)"
                  type="number"
                  value={collectionIntervalInput}
                  onChange={(e) => setCollectionIntervalInput(e.target.value)}
                  hint="NFR-01 enforces a strict upper limit of 10 minutes between polls."
                />
                <Input
                  label="Minimum Channels per Cluster (N)"
                  type="number"
                  value={minChannelsInput}
                  onChange={(e) => setMinChannelsInput(e.target.value)}
                  hint="Minimum distinct channels required to trigger a cluster alert."
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

              {saveMessage ? (
                <div
                  role="status"
                  className="rounded-xl border border-status-successBg bg-status-successBg p-3 text-xs font-semibold text-status-successText"
                >
                  <Icon name="circle-check" className="mr-1.5" />
                  {saveMessage}
                </div>
              ) : null}

              <div className="flex justify-end">
                <Button
                  type="submit"
                  variant="primary"
                  leftIcon="check"
                  isLoading={isSaving}
                >
                  Save & Bump Parameter Version
                </Button>
              </div>
            </form>
          </Card>
        )}
      </div>
    </AppShell>
  );
}

