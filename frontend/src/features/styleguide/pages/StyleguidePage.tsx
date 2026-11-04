import { useState } from 'react';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Icon,
  Input,
  Modal,
  Select,
  Skeleton,
  Table,
  Tabs,
  Tooltip,
  type TableColumn,
} from '../../../components/ui';

interface SampleChannelRow {
  id: string;
  handle: string;
  risk: 'low' | 'medium' | 'high';
  score: number;
}

const SAMPLE_ROWS: readonly SampleChannelRow[] = [
  { id: '1', handle: '@moldova_news_pulse', risk: 'high', score: 89 },
  { id: '2', handle: '@chisinau_express', risk: 'medium', score: 62 },
  { id: '3', handle: '@agro_journal_md', risk: 'low', score: 18 },
];

const SAMPLE_COLUMNS: readonly TableColumn<SampleChannelRow>[] = [
  {
    key: 'handle',
    header: 'Channel',
    render: (row) => <span className="font-semibold text-ink-primary">{row.handle}</span>,
  },
  {
    key: 'risk',
    header: 'Risk Band',
    render: (row) => <Badge variant={row.risk}>{row.risk.toUpperCase()}</Badge>,
  },
  {
    key: 'score',
    header: 'Coordination Score',
    align: 'right',
    render: (row) => <span className="font-bold text-ink-primary">{row.score}/100</span>,
  },
];

export function StyleguidePage() {
  const [activeRange, setActiveRange] = useState<'24h' | '7d' | '30d'>('7d');
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className="min-h-screen bg-surface-canvas p-6 md:p-10">
      <div className="mx-auto max-w-6xl space-y-8 rounded-shell bg-surface-app p-8 shadow-shell">
        <header className="flex flex-wrap items-center justify-between gap-4 border-b border-brand-200 pb-6">
          <div>
            <h1 className="text-2xl font-bold text-ink-primary">ScamGuard Design System</h1>
            <p className="mt-1 text-sm text-ink-muted">
              Tokenized UI primitives and Font Awesome icon registry (/styleguide)
            </p>
          </div>
          <Badge variant="brand" icon="shield-halved">
            Phase 1 Tokens Ready
          </Badge>
        </header>

        {/* Buttons */}
        <Card>
          <CardHeader title="Buttons" subtitle="Variants, sizes, and Font Awesome icon slots" />
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="primary" leftIcon="plus">
              Add Channel
            </Button>
            <Button variant="secondary" leftIcon="filter">
              Filter Clusters
            </Button>
            <Button variant="outline" rightIcon="download">
              Export CSV
            </Button>
            <Button variant="ghost" leftIcon="rotate-right">
              Refresh
            </Button>
            <Button variant="danger" leftIcon="trash">
              Remove
            </Button>
            <Button variant="primary" size="sm">
              Small
            </Button>
            <Button variant="primary" size="lg">
              Large Action
            </Button>
            <Button variant="primary" isLoading>
              Loading
            </Button>
          </div>
        </Card>

        {/* Badges & Tooltips */}
        <Card tone="banner">
          <CardHeader title="Badges & Tooltips" subtitle="Risk bands, narrative tags, and hover info" />
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="low" icon="circle-check">
              Low Risk (18)
            </Badge>
            <Badge variant="medium" icon="clock">
              Medium Risk (62)
            </Badge>
            <Badge variant="high" icon="triangle-exclamation">
              High Risk (89)
            </Badge>
            <Badge variant="brand" icon="layer-group">
              Energy Sanctions Narrative
            </Badge>
            <Badge variant="neutral" onDismiss={() => undefined}>
              Feb 1 to Mar 5
            </Badge>
            <Tooltip content="Score combines cluster share, copy delay, and pair repetition">
              <Button variant="outline" size="sm" leftIcon="circle-info">
                Hover for Explanation Tooltip
              </Button>
            </Tooltip>
          </div>
        </Card>

        {/* Form Controls & Tabs */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Card>
            <CardHeader title="Inputs & Selects" subtitle="Accessible form fields with validation" />
            <div className="space-y-4">
              <Input
                label="Search Channels or Messages"
                placeholder="Search for Statics..."
                leftIcon="magnifying-glass"
                hint="Supports channel handles (@name) and Romanian/Russian keywords."
              />
              <Input
                label="Telegram Username"
                defaultValue="invalid handle"
                error="Channel username must start with @ or t.me/"
              />
              <Select
                label="Narrative Category"
                options={[
                  { value: 'all', label: 'All Narratives' },
                  { value: 'eu', label: 'Anti-EU / Europe is falling apart' },
                  { value: 'elections', label: 'Moldova government and elections' },
                ]}
              />
            </div>
          </Card>

          <Card tone="chart">
            <CardHeader
              title="Tabs & Modal Trigger"
              subtitle="Segmented pill switcher and dialog overlay"
              action={
                <Tabs
                  items={[
                    { value: '24h', label: '24h' },
                    { value: '7d', label: '7d' },
                    { value: '30d', label: '30d' },
                  ]}
                  value={activeRange}
                  onChange={setActiveRange}
                />
              }
            />
            <div className="space-y-4">
              <p className="text-xs font-medium text-ink-secondary">
                Active range selected: <strong>{activeRange}</strong>
              </p>
              <Button variant="primary" leftIcon="eye" onClick={() => setIsModalOpen(true)}>
                Open Evidence Modal
              </Button>
              <div className="space-y-2 pt-2">
                <p className="text-xs font-semibold text-ink-muted">Skeleton Loading States</p>
                <div className="flex items-center gap-3">
                  <Skeleton variant="circle" />
                  <div className="flex-1 space-y-2">
                    <Skeleton variant="line" className="w-2/3" />
                    <Skeleton variant="line" className="w-1/2" />
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Table & Empty State */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div>
            <Table
              columns={SAMPLE_COLUMNS}
              data={SAMPLE_ROWS}
              rowKey={(row) => row.id}
            />
          </div>
          <EmptyState
            icon="satellite-dish"
            title="No Coordinated Clusters in Window"
            description="No channels exceeded the 0.85 similarity threshold within the last 60 minutes."
            action={
              <Button variant="secondary" size="sm" leftIcon="rotate-right">
                Re-scan Window
              </Button>
            }
          />
        </div>

        {/* Icon Showcase */}
        <Card tone="muted" padding="sm">
          <div className="flex flex-wrap items-center gap-4 text-ink-primary">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-muted">
              Font Awesome Icons:
            </span>
            <Icon name="gauge-high" title="Dashboard" />
            <Icon name="satellite-dish" title="Channels" />
            <Icon name="layer-group" title="Clusters" />
            <Icon name="gear" title="Settings" />
            <Icon name="envelope" title="Messages" />
            <Icon name="chart-pie" title="Analytics" />
            <Icon name="share-nodes" title="Integrations" />
            <Icon name="bell" title="Alerts" />
            <Icon name="clock" title="Timestamp" />
            <Icon name="hand-pointer" title="Subscribers" />
            <Icon name="users" title="Engagement" />
            <Icon name="circle-play" title="Watch time" />
          </div>
        </Card>

        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="Cluster Coordination Evidence"
          subtitle="Parameter Version v3 • Similarity Threshold ≥ 0.85"
          footer={
            <>
              <Button variant="ghost" onClick={() => setIsModalOpen(false)}>
                Close
              </Button>
              <Button variant="primary" onClick={() => setIsModalOpen(false)}>
                Confirm Review
              </Button>
            </>
          }
        >
          <p>
            4 channels posted near-identical claims within 9 minutes (cosine similarity 0.93).
          </p>
        </Modal>
      </div>
    </div>
  );
}

