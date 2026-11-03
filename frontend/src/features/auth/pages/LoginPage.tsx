import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AppShell } from '../../../components/layout';
import { Badge, Button, Card, Icon, Input } from '../../../components/ui';
import { authService, type IAuthService } from '../../../services/auth.service';

export interface LoginPageProps {
  service?: IAuthService;
}

export function LoginPage({ service = authService }: LoginPageProps) {
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState('elena.botnari@scamguard.md');
  const [password, setPassword] = useState('scamguard2026');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await service.login({
        email: identifier,
        username: !identifier.includes('@') ? identifier : undefined,
        login: identifier,
        password,
      });
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to sign in.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-md space-y-6 py-6">
        <Card tone="banner" padding="lg" className="space-y-2">
          <div className="flex items-center justify-between">
            <Badge variant="brand" icon="shield-halved">
              Researcher Access
            </Badge>
            <Icon name="lock" className="text-brand-500" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">
            Sign in to ChorusWatch
          </h1>
          <p className="text-xs font-medium text-ink-muted">
            Authenticate as a journalist or administrator to monitor watchlists, analyze clusters, and export reports
          </p>
        </Card>

        <Card>
          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4" noValidate>
            <Input
              label="Work or Newsroom Email / Username"
              type="text"
              leftIcon="user"
              placeholder="username or journalist@newsroom.md"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
            />
            <Input
              label="Password"
              type="password"
              leftIcon="lock"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            {error ? (
              <div
                role="alert"
                className="rounded-xl border border-status-danger/30 bg-status-dangerBg p-3 text-xs font-semibold text-status-dangerText"
              >
                <Icon name="triangle-exclamation" className="mr-1.5" />
                {error}
              </div>
            ) : null}

            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              className="w-full"
              rightIcon="arrow-right"
            >
              Sign In
            </Button>
          </form>

          <div className="mt-4 flex items-center justify-between border-t border-brand-100 pt-4 text-xs text-ink-muted">
            <span>New investigative researcher?</span>
            <Link to="/register" className="font-bold text-brand-600 hover:underline">
              Create Researcher Account
            </Link>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
