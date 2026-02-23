import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';
import ToastProvider from './components/Toast';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Ingredients from './pages/Ingredients';
import Recipes from './pages/Recipes';
import RecipeDetail from './pages/RecipeDetail';
import RecipeNew from './pages/RecipeNew';
import RecipeEdit from './pages/RecipeEdit';
import Onboarding from './pages/Onboarding';
import Invoices from './pages/Invoices';
import InvoiceUpload from './pages/InvoiceUpload';
import InvoiceReview from './pages/InvoiceReview';
import Alerts from './pages/Alerts';
import Simulator from './pages/Simulator';
import SimulatorHome from './pages/SimulatorHome';
import Pricing from './pages/Pricing';
import Settings from './pages/Settings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
      <BrowserRouter>
        <ToastProvider />
        <Routes>
          {/* Public routes */}
          <Route path="/landing" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/auth/callback" element={<AuthCallback />} />

          {/* Protected routes */}
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Dashboard />} />
            <Route path="/ingredients" element={<Ingredients />} />
            <Route path="/recipes" element={<Recipes />} />
            <Route path="/recipes/new" element={<RecipeNew />} />
            <Route path="/recipes/:id" element={<RecipeDetail />} />
            <Route path="/recipes/:id/edit" element={<RecipeEdit />} />
            <Route path="/recipes/:id/simulate" element={<Simulator />} />
            <Route path="/simulator" element={<SimulatorHome />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/onboarding" element={<Onboarding />} />
            <Route path="/invoices" element={<Invoices />} />
            <Route path="/invoices/upload" element={<InvoiceUpload />} />
            <Route path="/invoices/:id/review" element={<InvoiceReview />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
