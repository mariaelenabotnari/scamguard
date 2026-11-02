import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';
import { Badge, Button, Card } from '../components/ui';
import { StyleguidePage } from '../features/styleguide/pages/StyleguidePage';

function HomePlaceholderPage() {
  return (
    <main className="min-h-screen bg-surface-canvas p-8">
      <div className="mx-auto max-w-4xl">
        <Card className="space-y-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-ink-primary">Scamguard</h1>
            <Badge variant="brand" icon="shield-halved">
              Moldova Telegram Monitor
            </Badge>
          </div>
          <p className="text-sm text-ink-secondary">
            Coordinated Telegram channel activity detection and narrative analysis platform.
          </p>
          <div>
            <Link to="/styleguide">
              <Button variant="secondary" size="sm" rightIcon="arrow-right">
                View Design System Styleguide
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    </main>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomePlaceholderPage />} />
      <Route path="/styleguide" element={<StyleguidePage />} />
    </Routes>
  );
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

