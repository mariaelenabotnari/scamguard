import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Badge, Button, Card, Icon, Input } from '../../../components/ui';
import { authService, type IAuthService } from '../../../services/auth.service';
import { AuthLayout } from '../components/AuthLayout';

export interface RegisterPageProps {
  service?: IAuthService;
}

export function RegisterPage({ service = authService }: RegisterPageProps) {
  const navigate = useNavigate();
  const [step, setStep] = useState<'register' | 'verify'>('register');
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [organization, setOrganization] = useState('');
  const [password, setPassword] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [devCode, setDevCode] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleRegisterSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setInfoMessage(null);
    setIsSubmitting(true);
    try {
      const response = await service.register({
        username: username.trim() || undefined,
        fullName: fullName.trim(),
        email: email.trim(),
        organization: organization.trim() || 'Independent Researcher',
        password,
      });
      if (response && response.requiresVerification) {
        setDevCode(response.code ?? null);
        setStep('verify');
      } else {
        navigate('/');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifySubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setInfoMessage(null);
    setIsSubmitting(true);
    try {
      await service.verifyEmail({
        email: email.trim(),
        code: verificationCode.trim(),
      });
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResendCode = async () => {
    setError(null);
    try {
      const res = await service.resendCode(email.trim());
      if (res.code) {
        setDevCode(res.code);
      }
      setInfoMessage('A new verification code has been sent to your email.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to resend code.');
    }
  };

  return (
    <AuthLayout>
      <div className="space-y-5">
        <Card tone="banner" padding="lg" className="space-y-2">
          <Badge variant="brand" icon="user-shield">
            {step === 'register' ? 'Self-Registration (Journalist Role)' : 'Account Activation'}
          </Badge>
          <h1 className="text-2xl font-extrabold tracking-tight text-ink-primary">
            {step === 'register' ? 'Create Researcher Account' : 'Verify Your Email'}
          </h1>
          <p className="text-xs font-medium text-ink-muted">
            {step === 'register'
              ? 'New researcher accounts start with a clean workspace to investigate Telegram channels and coordination patterns.'
              : `Enter the 6-digit confirmation code sent to ${email || 'your email'} to activate your account.`}
          </p>
        </Card>

        <Card>
          {step === 'register' ? (
            <form onSubmit={(e) => void handleRegisterSubmit(e)} className="space-y-4" noValidate>
              <Input
                label="Full Name"
                leftIcon="user"
                placeholder="Maria Elena Botnari"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
              <Input
                label="Username"
                leftIcon="user"
                placeholder="maria_botnari"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
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

              <div className="mt-4 flex items-center justify-between border-t border-brand-100 pt-4 text-xs text-ink-muted">
                <span>Already have an account?</span>
                <Link to="/login" className="font-bold text-brand-600 hover:underline">
                  Sign In
                </Link>
              </div>
            </form>
          ) : (
            <form onSubmit={(e) => void handleVerifySubmit(e)} className="space-y-4" noValidate>
              {devCode ? (
                <div className="rounded-xl border border-brand-200 bg-brand-50 p-3 text-xs text-brand-900">
                  <div className="flex items-center gap-2 font-semibold">
                    <Icon name="envelope" className="text-brand-600" />
                    <span>Demo Verification Code</span>
                  </div>
                  <p className="mt-1 text-[11px] text-ink-muted">
                    In development/preview mode, use code:{' '}
                    <span className="font-mono font-bold tracking-widest text-brand-700">
                      {devCode}
                    </span>
                  </p>
                </div>
              ) : null}

              {infoMessage ? (
                <div className="rounded-xl border border-status-success/30 bg-status-successBg p-3 text-xs font-semibold text-status-successText">
                  <Icon name="circle-check" className="mr-1.5" />
                  {infoMessage}
                </div>
              ) : null}

              <Input
                label="6-Digit Verification Code"
                leftIcon="lock"
                placeholder="123456"
                maxLength={6}
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
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
                Verify &amp; Start Investigation
              </Button>

              <div className="flex items-center justify-between border-t border-brand-100 pt-3 text-xs">
                <button
                  type="button"
                  onClick={() => setStep('register')}
                  className="font-medium text-ink-muted hover:text-ink-primary hover:underline"
                >
                  ← Edit details
                </button>
                <button
                  type="button"
                  onClick={() => void handleResendCode()}
                  className="font-semibold text-brand-600 hover:underline"
                >
                  Resend code
                </button>
              </div>
            </form>
          )}
        </Card>
      </div>
    </AuthLayout>
  );
}
