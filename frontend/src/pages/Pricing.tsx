import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import toast from 'react-hot-toast';
import { usePlanInfo, createCheckout } from '../hooks/useBilling';

const plans = [
  {
    key: 'free',
    name: 'Free',
    price: 'Gratuit',
    period: '',
    features: ['5 recettes', '3 factures/mois', 'Dashboard', 'Onboarding AI'],
    highlight: false,
  },
  {
    key: 'pro',
    name: 'Pro',
    price: '14,90\u00a0\u20ac',
    period: '/mois',
    features: [
      'Recettes illimitées',
      'Factures illimitées',
      'Alertes email',
      'Export CSV',
    ],
    highlight: true,
  },
  {
    key: 'multi',
    name: 'Multi',
    price: '24,90\u00a0\u20ac',
    period: '/mois',
    features: [
      'Tout Pro',
      "Jusqu'à 5 établissements",
      'Dashboard consolidé',
    ],
    highlight: false,
  },
];

export default function Pricing() {
  const navigate = useNavigate();
  const { data: planInfo } = usePlanInfo();
  const currentPlan = planInfo?.current_plan || 'free';
  const [loading, setLoading] = useState<string | null>(null);

  async function handleUpgrade(planKey: string) {
    if (planKey === 'free' || planKey === currentPlan) return;
    setLoading(planKey);
    try {
      const url = await createCheckout(planKey);
      window.location.href = url;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erreur');
      setLoading(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-stone-500 hover:text-stone-700">
          <ArrowLeft size={20} />
        </button>
        <h1 className="text-xl font-bold text-stone-900">Plans & tarifs</h1>
      </div>

      <div className="grid gap-4">
        {plans.map((plan) => {
          const isCurrent = plan.key === currentPlan;
          return (
            <div
              key={plan.key}
              className={`rounded-xl p-5 border-2 ${
                plan.highlight
                  ? 'border-orange-700 bg-orange-50'
                  : 'border-stone-200 bg-white'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold text-stone-900">{plan.name}</h3>
                  <div className="mt-1">
                    <span className="text-2xl font-bold text-stone-900">{plan.price}</span>
                    <span className="text-stone-500 text-sm">{plan.period}</span>
                  </div>
                </div>
                {plan.highlight && (
                  <span className="bg-orange-700 text-white text-xs font-bold px-2 py-1 rounded-full">
                    Recommandé
                  </span>
                )}
              </div>
              <ul className="mt-3 space-y-1.5">
                {plan.features.map((f, j) => (
                  <li key={j} className="flex items-center gap-2 text-sm text-stone-700">
                    <span className="text-green-600">✓</span> {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => handleUpgrade(plan.key)}
                disabled={isCurrent || loading === plan.key}
                className={`mt-4 w-full py-2.5 rounded-lg font-medium transition-colors ${
                  isCurrent
                    ? 'bg-stone-100 text-stone-400 cursor-default'
                    : plan.highlight
                    ? 'bg-orange-700 text-white hover:bg-orange-800 disabled:opacity-50'
                    : 'border border-stone-300 text-stone-700 hover:bg-stone-50 disabled:opacity-50'
                }`}
              >
                {isCurrent
                  ? 'Plan actuel'
                  : loading === plan.key
                  ? 'Redirection...'
                  : `Passer au ${plan.name}`}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
