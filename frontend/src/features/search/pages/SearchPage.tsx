import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AppShell } from '../../../components/layout';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Skeleton,
  Tabs,
} from '../../../components/ui';
import type { UnifiedSearchResultsDto } from '../../../dtos/search.dto';
import {
  searchService,
  type ISearchService,
} from '../../../services/search.service';

export interface SearchPageProps {
  service?: ISearchService;
}

type SearchTab = 'all' | 'channels' | 'messages' | 'clusters';

export function SearchPage({ service = searchService }: SearchPageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') ?? '';
  const [queryInput, setQueryInput] = useState<string>(initialQuery);
  const [activeTab, setActiveTab] = useState<SearchTab>('all');
  const [results, setResults] = useState<UnifiedSearchResultsDto | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const paramQ = searchParams.get('q');
    if (paramQ !== null && paramQ !== queryInput) {
      setQueryInput(paramQ);
    }
  }, [searchParams, queryInput]);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    service
      .searchAll(queryInput)
      .then((data) => {
        if (isMounted) {
          setResults(data);
          setIsLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Search request failed.');
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [queryInput, service]);

  const handleQueryChange = (value: string) => {
    setQueryInput(value);
    if (value.trim()) {
      setSearchParams({ q: value });
    } else {
      setSearchParams({});
    }
  };

  const tabItems: readonly { value: SearchTab; label: string; count?: number }[] = [
    {
      value: 'all',
      label: 'All Results',
      count: results
        ? results.channels.length + results.messages.length + results.clusters.length
        : undefined,
    },
    { value: 'channels', label: 'Channels', count: results?.channels.length },
    { value: 'messages', label: 'Messages', count: results?.messages.length },
    { value: 'clusters', label: 'Clusters', count: results?.clusters.length },
  ];

  const showChannels = activeTab === 'all' || activeTab === 'channels';
  const showMessages = activeTab === 'all' || activeTab === 'messages';
  const showClusters = activeTab === 'all' || activeTab === 'clusters';

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">
              Search Results
            </h1>
            <p className="mt-0.5 text-xs font-medium text-ink-muted">
              Search across watched channels, individual messages, and multi-channel clusters.
            </p>
          </div>
        </div>

        {/* Search Input & Result Type Tabs */}
        <Card padding="sm" className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div className="w-full lg:max-w-md">
            <Input
              aria-label="Search channels, messages, and clusters"
              placeholder="Search channels, messages or clusters..."
              leftIcon="magnifying-glass"
              value={queryInput}
              onChange={(e) => handleQueryChange(e.target.value)}
            />
          </div>

          <Tabs
            ariaLabel="Search result categories"
            variant="soft"
            items={tabItems}
            value={activeTab}
            onChange={setActiveTab}
          />
        </Card>

        {isLoading ? (
          <div aria-label="Loading search results" className="space-y-3">
            <Skeleton variant="block" className="h-24 w-full" />
            <Skeleton variant="block" className="h-24 w-full" />
          </div>
        ) : error ? (
          <EmptyState
            icon="triangle-exclamation"
            title="Search Failed"
            description={error}
          />
        ) : results &&
          results.channels.length === 0 &&
          results.messages.length === 0 &&
          results.clusters.length === 0 ? (
          <EmptyState
            icon="magnifying-glass"
            title="No Matching Records"
            description={`No channels, messages, or clusters matched "${queryInput}".`}
          />
        ) : results ? (
          <div className="space-y-6">
            {/* Channels Section */}
            {showChannels && results.channels.length > 0 ? (
              <section aria-label="Matching channels" className="space-y-3">
                <h2 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
                  Channels ({results.channels.length})
                </h2>
                {results.channels.map((ch) => (
                  <Card
                    key={ch.id}
                    padding="sm"
                    className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center"
                  >
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          to={`/channels/${ch.id}`}
                          className="text-sm font-extrabold text-ink-primary hover:text-brand-700 hover:underline"
                        >
                          {ch.handle}
                        </Link>
                        <Badge
                          variant={ch.score >= 70 ? 'high' : ch.score >= 40 ? 'medium' : 'low'}
                        >
                          {ch.score >= 70 ? 'HIGH' : ch.score >= 40 ? 'MEDIUM' : 'LOW'} {ch.score}
                        </Badge>
                        <Badge variant="brand">{ch.primaryNarrative}</Badge>
                      </div>
                      <p className="text-xs text-ink-secondary">
                        <span className="font-semibold text-brand-700">Found because (Score Explanation):</span>{' '}
                        {ch.explanation.summary}
                      </p>
                    </div>
                    <Link to={`/channels/${ch.id}`}>
                      <Button variant="secondary" size="sm" rightIcon="chevron-right">
                        Inspect Channel
                      </Button>
                    </Link>
                  </Card>
                ))}
              </section>
            ) : null}

            {/* Messages Section */}
            {showMessages && results.messages.length > 0 ? (
              <section aria-label="Matching messages" className="space-y-3">
                <h2 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
                  Messages ({results.messages.length})
                </h2>
                {results.messages.map((msg) => (
                  <Card key={msg.id} padding="sm" className="space-y-2.5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          to={`/channels/${msg.channelId}`}
                          className="text-xs font-extrabold text-ink-primary hover:underline"
                        >
                          {msg.handle}
                        </Link>
                        <Badge
                          variant={msg.channelScore >= 70 ? 'high' : msg.channelScore >= 40 ? 'medium' : 'low'}
                        >
                          Risk {msg.channelScore}
                        </Badge>
                        <Badge variant="brand">{msg.narrativeCategory}</Badge>
                      </div>
                      <span className="text-[11px] font-medium text-ink-muted">
                        {msg.postedAt}
                      </span>
                    </div>

                    <p className="rounded-badge bg-surface-muted p-3 text-xs text-ink-primary">
                      “{msg.snippet}”
                    </p>

                    <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-ink-secondary">
                      <span>
                        <span className="font-semibold text-brand-700">Found because:</span>{' '}
                        {msg.explanation.summary}
                      </span>
                      {msg.clusterId ? (
                        <Link to={`/clusters/${msg.clusterId}`}>
                          <Button variant="outline" size="sm" rightIcon="arrow-right">
                            View In Cluster
                          </Button>
                        </Link>
                      ) : null}
                    </div>
                  </Card>
                ))}
              </section>
            ) : null}

            {/* Clusters Section */}
            {showClusters && results.clusters.length > 0 ? (
              <section aria-label="Matching clusters" className="space-y-3">
                <h2 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
                  Clusters ({results.clusters.length})
                </h2>
                {results.clusters.map((cl) => (
                  <Card
                    key={cl.id}
                    padding="sm"
                    className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center"
                  >
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-extrabold text-ink-primary">
                          {cl.headlineSummary}
                        </span>
                        <Badge variant="brand">{cl.narrativeCategory}</Badge>
                        <Badge variant="high">
                          {Math.round(cl.averageSimilarity * 100)}% Match
                        </Badge>
                      </div>
                      <p className="text-xs text-ink-muted">“{cl.representativeSnippet}”</p>
                    </div>
                    <Link to={`/clusters/${cl.id}`}>
                      <Button variant="primary" size="sm" rightIcon="chevron-right">
                        Inspect Cluster
                      </Button>
                    </Link>
                  </Card>
                ))}
              </section>
            ) : null}
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
