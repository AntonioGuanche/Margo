import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';

interface PlanInfo {
  current_plan: string;
  max_recipes: number | null;
  max_invoices_per_month: number | null;
  current_recipes: number;
  current_invoices_this_month: number;
  stripe_customer_id: string | null;
  can_manage_billing: boolean;
}

interface CheckoutResponse {
  checkout_url: string;
}

interface PortalResponse {
  portal_url: string;
}

export function usePlanInfo() {
  return useQuery<PlanInfo>({
    queryKey: ['plan-info'],
    queryFn: () => apiClient<PlanInfo>('/api/billing/plan'),
  });
}

export async function createCheckout(plan: string): Promise<string> {
  const data = await apiClient<CheckoutResponse>('/api/billing/checkout', {
    method: 'POST',
    body: {
      plan,
      success_url: `${window.location.origin}/settings?checkout=success`,
      cancel_url: `${window.location.origin}/pricing`,
    },
  });
  return data.checkout_url;
}

export async function openCustomerPortal(): Promise<string> {
  const data = await apiClient<PortalResponse>('/api/billing/portal', {
    method: 'POST',
  });
  return data.portal_url;
}
