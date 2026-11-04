import React, { useEffect, useState } from 'react';
import { AppShell } from '../../../components/layout';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Icon,
  Input,
  Skeleton,
} from '../../../components/ui';
import type { SystemParametersDto } from '../../../dtos/admin.dto';
import { adminService, type IAdminService } from '../../../services/admin.service';

export interface AdminSettingsPageProps {
  service?: IAdminService;
}

type AdminTab = 'parameters' | 'users' | 'audit';

interface MockUser {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'journalist' | 'visitor';
  lastActive: string;
}

interface MockAuditLogItem {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  details: string;
}

const MOCK_USERS: MockUser[] = [
  {
    id: 'usr-1',
    name: 'Elena Botnari',
    email: 'elena.botnari@scamguard.md',
    role: 'admin',
    lastActive: 'Today, 14:15',
  },
  {
    id: 'usr-2',
    name: 'Ion Rusu',
    email: 'ion.rusu@mediawatch.md',
    role: 'journalist',
    lastActive: 'Yesterday, 18:30',
  },
  {
    id: 'usr-3',
    name: 'Tatiana Morari',
    email: 't.morari@civicpress.md',
    role: 'journalist',
    lastActive: 'Oct 31, 09:20',
  },
];

const MOCK_AUDIT_LOGS: MockAuditLogItem[] = [
  {
    id: 'aud-1',
    timestamp: 'Today, 11:20',
    user: 'elena.botnari',
    action: 'Updated Parameters',
    details: 'Changed similarity threshold to 0.85, window to 30m (v3)',
  },
  {
    id: 'aud-2',
    timestamp: 'Nov 02, 14:05',
    user: 'elena.botnari',
    action: 'Added Channel',
    details: 'Added @gagauzia_voice_md to watched channels',
  },
  {
    id: 'aud-3',
    timestamp: 'Nov 01, 16:45',
    user: 'ion.rusu',
    action: 'Paused Channel',
    details: 'Paused collection for @agro_journal_md',
  },
  {
    id: 'aud-4',
    timestamp: 'Oct 30, 08:12',
    user: 'elena.botnari',
    action: 'Exported Dataset',
    details: 'Exported CSV of 48 coordinated clusters',
  },
];

const INITIAL_PARAMETERS: SystemParametersDto = {
  parameterVersion: 'v1.4',
  similarityThreshold: 0.82,
  timeWindowMinutes: 30,
  collectionIntervalMinutes: 5,
  minClusterChannels: 3,
  updatedAt: '2026-11-02 12:00',
  updatedBy: 'elena.botnari@scamguard.md',
};

export function AdminSettingsPage({ service = adminService }: AdminSettingsPageProps) {
  const [activeTab, setActiveTab] = useState<AdminTab>('parameters');
  const [params, setParams] = useState<SystemParametersDto>(INITIAL_PARAMETERS);
  const [isLoading, setIsLoading] = useState(false);
  const [similarityInput, setSimilarityInput] = useState('0.82');
  const [timeWindowInput, setTimeWindowInput] = useState('30');
  const [collectionIntervalInput, setCollectionIntervalInput] = useState('5');
  const [minChannelsInput, setMinChannelsInput] = useState('3');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let isMounted = true;
    service
      .getParameters()
      .then((data) => {
        if (isMounted) {
          setParams(data);
          setSimilarityInput(String(data.similarityThreshold));
          setTimeWindowInput(String(data.timeWindowMinutes));
          setCollectionIntervalInput(String(data.collectionIntervalMinutes));
          setMinChannelsInput(String(data.minClusterChannels));
          setIsLoading(false);
        }
      })
      .catch(() => {
        // Fallback to initial state
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
        `Saved new parameter version ${updated.parameterVersion}. Historical scores keep their original version tag.`,
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
        {/* Page Header */}
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">
              Settings
            </h1>
            <p className="mt-0.5 text-xs font-medium text-ink-muted">
              Configure detection parameters, manage researcher access, and review the audit log.
            </p>
          </div>
          {params ? (
            <Badge variant="brand" icon="sliders">
              {`Active Parameter Set: ${params.parameterVersion}`}
            </Badge>
          ) : null}
        </div>

        {/* Settings Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-brand-100 pb-2">
          <button
            type="button"
            onClick={() => setActiveTab('parameters')}
            className={`rounded-badge px-4 py-2 text-xs font-bold transition-all ${
              activeTab === 'parameters'
                ? 'bg-brand-700 text-white shadow-xs'
                : 'bg-surface-card text-ink-muted hover:text-ink-primary'
            }`}
          >
            Detection Parameters
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('users')}
            className={`rounded-badge px-4 py-2 text-xs font-bold transition-all ${
              activeTab === 'users'
                ? 'bg-brand-700 text-white shadow-xs'
                : 'bg-surface-card text-ink-muted hover:text-ink-primary'
            }`}
          >
            Users & Roles ({MOCK_USERS.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('audit')}
            className={`rounded-badge px-4 py-2 text-xs font-bold transition-all ${
              activeTab === 'audit'
                ? 'bg-brand-700 text-white shadow-xs'
                : 'bg-surface-card text-ink-muted hover:text-ink-primary'
            }`}
          >
            Audit Log
          </button>
        </div>

        {/* Tab 1: Detection Parameters */}
        {activeTab === 'parameters' ? (
          isLoading ? (
            <div aria-label="Loading admin parameters" className="space-y-3">
              <Skeleton variant="block" className="h-44 w-full" />
            </div>
          ) : (
            <Card className="p-6">
              <form onSubmit={(e) => void handleSubmit(e)} className="space-y-5" noValidate>
                <CardHeader
                  title="Detection Thresholds"
                  subtitle="Parameters used by the pipeline to link duplicate messages and flag coordinated cascades."
                />

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <Input
                    label="Similarity Threshold (0.50 – 0.99)"
                    type="number"
                    step="0.01"
                    value={similarityInput}
                    onChange={(e) => setSimilarityInput(e.target.value)}
                    hint="Minimum text similarity score required to match two posts."
                  />
                  <Input
                    label="Time Window (minutes)"
                    type="number"
                    value={timeWindowInput}
                    onChange={(e) => setTimeWindowInput(e.target.value)}
                    hint="Maximum time elapsed between posts for them to be considered coordinated."
                  />
                  <Input
                    label="Minimum Channels per Cluster"
                    type="number"
                    value={minChannelsInput}
                    onChange={(e) => setMinChannelsInput(e.target.value)}
                    hint="Minimum distinct channels required to group messages into a cluster."
                  />
                  <Input
                    label="Collector Poll Interval (minutes, max 10)"
                    type="number"
                    value={collectionIntervalInput}
                    onChange={(e) => setCollectionIntervalInput(e.target.value)}
                    hint="Frequency of checks for new posts across watched channels."
                  />
                </div>

                {/* Advanced Fold */}
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAdvanced((prev) => !prev)}
                    className="inline-flex items-center gap-1.5 text-xs font-bold text-brand-700 hover:text-brand-800"
                  >
                    <Icon name={showAdvanced ? 'chevron-up' : 'chevron-down'} className="text-[10px]" />
                    <span>{showAdvanced ? 'Hide advanced settings' : 'Show advanced algorithm settings'}</span>
                  </button>

                  {showAdvanced ? (
                    <div className="mt-3 rounded-card border border-brand-100 bg-surface-muted/40 p-4 text-xs space-y-2">
                      <p className="font-semibold text-ink-primary">Multilingual Semantic Embeddings:</p>
                      <p className="text-ink-secondary">
                        Uses sentence transformer embeddings normalized across Romanian and Russian texts with cosine distance thresholding.
                      </p>
                      <p className="font-semibold text-ink-primary pt-2">Near-Duplicate MinHash LSH:</p>
                      <p className="text-ink-secondary">
                        128 permutation hashes with 8 bands for fast Jaccard similarity pre-filtering before semantic scoring.
                      </p>
                    </div>
                  ) : null}
                </div>

                {error ? (
                  <div
                    role="alert"
                    className="rounded-xl border border-status-dangerText/30 bg-status-dangerBg p-3 text-xs font-semibold text-status-dangerText"
                  >
                    <Icon name="triangle-exclamation" className="mr-1.5" />
                    {error}
                  </div>
                ) : null}

                {saveMessage ? (
                  <div
                    role="status"
                    className="rounded-xl bg-status-successBg p-3 text-xs font-semibold text-status-successText"
                  >
                    <Icon name="circle-check" className="mr-1.5" />
                    {saveMessage}
                  </div>
                ) : null}

                <div className="flex justify-end pt-2">
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
          )
        ) : null}

        {/* Tab 2: Users & Roles */}
        {activeTab === 'users' ? (
          <Card className="p-6">
            <CardHeader
              title="Team Members & Access Roles"
              subtitle="Authorized researchers and administrators"
              action={
                <Button variant="primary" size="sm" leftIcon="plus">
                  Invite Member
                </Button>
              }
            />

            <div className="mt-4 divide-y divide-brand-100/60">
              {MOCK_USERS.map((user) => (
                <div key={user.id} className="flex items-center justify-between py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 font-bold text-xs text-brand-800">
                      {user.name.split(' ').map((n) => n[0]).join('')}
                    </div>
                    <div>
                      <p className="text-xs font-bold text-ink-primary">{user.name}</p>
                      <p className="text-[11px] text-ink-muted">{user.email}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-[11px] text-ink-muted hidden sm:inline">
                      Active: {user.lastActive}
                    </span>
                    <Badge variant={user.role === 'admin' ? 'brand' : 'neutral'}>
                      {user.role.toUpperCase()}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        ) : null}

        {/* Tab 3: Audit Log */}
        {activeTab === 'audit' ? (
          <Card className="p-6">
            <CardHeader
              title="Audit Log"
              subtitle="Chronological log of administrative actions, parameter changes, and exports"
            />

            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-brand-100 bg-surface-muted/40 text-[10px] font-bold uppercase tracking-wider text-ink-muted">
                    <th className="px-4 py-2.5">Timestamp</th>
                    <th className="px-4 py-2.5">User</th>
                    <th className="px-4 py-2.5">Action</th>
                    <th className="px-4 py-2.5">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-brand-100/50">
                  {MOCK_AUDIT_LOGS.map((item) => (
                    <tr key={item.id} className="hover:bg-surface-banner/20">
                      <td className="px-4 py-3 text-ink-muted font-mono text-[11px]">
                        {item.timestamp}
                      </td>
                      <td className="px-4 py-3 font-semibold text-ink-primary">
                        {item.user}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="neutral">{item.action}</Badge>
                      </td>
                      <td className="px-4 py-3 text-ink-secondary">
                        {item.details}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ) : null}
      </div>
    </AppShell>
  );
}
