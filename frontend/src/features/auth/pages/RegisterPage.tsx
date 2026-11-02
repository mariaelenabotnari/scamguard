import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AppShell } from '../../../components/layout';
import { Badge, Button, Card, Icon, Input } from '../../../components/ui';
import { authService, type IAuthService } from '../../../services/auth.service';

export interface RegisterPageProps {
  service?: IAuthService;
}

export function RegisterPage({ service = authService }: RegisterPageProps) {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [organization, setOrganization] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await service.register({ fullName, email, organization, password });
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-md space-y-6 py-6">
        <Card tone="banner" padding="lg" className="space-y-2">
          <Badge variant="brand" icon="user-shield">
            Self-Registration (Journalist Role)
          </Badge>
          <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">
            Create Researcher Account
          </h1>
          <p className="text-xs font-medium text-ink-muted">
            New accounts start with NFR-10 anti-abuse export caps (250 rows/export, 3 exports/day)
            for the first 7 days
          </p>
        </Card>

        <Card>
          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4" noValidate>
            <Input
              label="Full Name"
              leftIcon="user"
              placeholder="Maria Elena Botnari"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
            <Input
              label="Newsroom or Academic Email"
              type="email"
              leftIcon="envelope"
              placeholder="maria@civicmedia.md"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Input
              label="Organization / Newsroom"
              leftIcon="briefcase"
              placeholder="Moldova Civic Media Lab"
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
            />
            <Input
              label="Password (min. 8 characters)"
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
              Register Journalist Account
            </Button>
          </form>

          <div className="mt-4 flex items-center justify-between border-t border-brand-100 pt-4 text-xs text-ink-muted">
            <span>Already have an account?</span>
            <Link to="/login" className="font-bold text-brand-600 hover:underline">
              Sign In
            </Link>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}

