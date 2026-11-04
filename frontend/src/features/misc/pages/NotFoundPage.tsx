import { Link } from 'react-router-dom';
import { AppShell } from '../../../components/layout';
import { Button, EmptyState } from '../../../components/ui';

export function NotFoundPage() {
  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          icon="triangle-exclamation"
          title="Page Not Found (404)"
          description="The requested route does not exist in the ScamGuard monitoring workspace."
          action={
            <Link to="/">
              <Button variant="primary" size="sm" rightIcon="arrow-right">
                Return to Overview Dashboard
              </Button>
            </Link>
          }
        />
      </div>
    </AppShell>
  );
}

