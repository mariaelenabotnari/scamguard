import { Link } from 'react-router-dom';
import { AppShell } from '../../../components/layout';
import { Button, EmptyState } from '../../../components/ui';

export function UnauthorizedPage() {
  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          icon="lock"
          title="Insufficient Role Permissions (403)"
          description="Your current account role does not have access to this administrative or journalist resource. Sign in with an authorized account or return to the public dashboard."
          action={
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Link to="/">
                <Button variant="secondary" size="sm">
                  Back to Dashboard
                </Button>
              </Link>
              <Link to="/login">
                <Button variant="primary" size="sm" rightIcon="arrow-right">
                  Switch Account
                </Button>
              </Link>
            </div>
          }
        />
      </div>
    </AppShell>
  );
}

