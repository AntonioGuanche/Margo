import { useState } from 'react';
import {
  Users,
  TrendingUp,
  BookOpen,
  UtensilsCrossed,
  FileText,
  RefreshCw,
  Shield,
  Loader2,
  Wrench,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  useAdminStats,
  useAdminUsers,
  useUpdateUserPlan,
  useNormalizeUnits,
  useFixInflatedPrices,
} from '../hooks/useAdmin';
import type { AdminUser } from '../types';

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Format a date in fr-BE locale. */
function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('fr-BE', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

/** Relative time label (French). */
function timeAgo(iso: string | null): string {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `il y a ${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `il y a ${days}j`;
  const months = Math.floor(days / 30);
  return `il y a ${months} mois`;
}

const PLAN_OPTIONS = ['free', 'pro', 'enterprise'] as const;

function planBadgeClass(plan: string): string {
  switch (plan) {
    case 'pro':
      return 'bg-orange-100 text-orange-700';
    case 'enterprise':
      return 'bg-emerald-100 text-emerald-700';
    default:
      return 'bg-stone-100 text-stone-600';
  }
}

/* ------------------------------------------------------------------ */
/*  Stat Card                                                          */
/* ------------------------------------------------------------------ */

function StatCard({
  label,
  value,
  icon: Icon,
  sub,
}: {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  sub?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-stone-200 p-4">
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 rounded-lg bg-orange-50">
          <Icon size={18} className="text-orange-600" />
        </div>
        <span className="text-sm text-stone-500">{label}</span>
      </div>
      <p className="text-2xl font-bold text-stone-900">{value}</p>
      {sub && <p className="text-xs text-stone-400 mt-1">{sub}</p>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  User Row (desktop)                                                 */
/* ------------------------------------------------------------------ */

function UserRow({ user }: { user: AdminUser }) {
  const [showPlanDropdown, setShowPlanDropdown] = useState(false);
  const updatePlan = useUpdateUserPlan();
  const normalizeUnits = useNormalizeUnits();
  const fixPrices = useFixInflatedPrices();
  const [normalizing, setNormalizing] = useState(false);
  const [fixing, setFixing] = useState(false);

  function handlePlanChange(plan: string) {
    setShowPlanDropdown(false);
    updatePlan.mutate(
      { id: user.id, plan },
      {
        onSuccess: () => toast.success(`Plan mis à jour → ${plan}`),
        onError: (err) => toast.error(err.message),
      },
    );
  }

  function handleNormalize() {
    setNormalizing(true);
    normalizeUnits.mutate(user.id, {
      onSuccess: (data) => {
        toast.success(
          `${data.ingredients_fixed} ingrédient(s) corrigé(s), ${data.recipes_recalculated} recette(s) recalculée(s)`,
        );
        setNormalizing(false);
      },
      onError: (err) => {
        toast.error(err.message);
        setNormalizing(false);
      },
    });
  }

  function handleFixPrices() {
    setFixing(true);
    fixPrices.mutate(user.id, {
      onSuccess: (data) => {
        toast.success(
          `${data.prices_fixed} prix corrigé(s), ${data.recipes_recalculated} recette(s) recalculée(s)`,
        );
        setFixing(false);
      },
      onError: (err) => {
        toast.error(err.message);
        setFixing(false);
      },
    });
  }

  return (
    <tr className="border-b border-stone-100 hover:bg-stone-50/50">
      <td className="py-3 px-3">
        <p className="font-medium text-stone-900 text-sm">{user.name}</p>
        <p className="text-xs text-stone-400">{user.owner_email}</p>
      </td>
      <td className="py-3 px-3 relative">
        <button
          onClick={() => setShowPlanDropdown(!showPlanDropdown)}
          className={`text-xs font-medium px-2.5 py-1 rounded-full cursor-pointer ${planBadgeClass(user.plan)}`}
        >
          {user.plan}
        </button>
        {showPlanDropdown && (
          <div className="absolute z-10 mt-1 bg-white border border-stone-200 rounded-lg shadow-lg py-1 min-w-[100px]">
            {PLAN_OPTIONS.map((p) => (
              <button
                key={p}
                onClick={() => handlePlanChange(p)}
                className={`block w-full text-left px-3 py-1.5 text-sm hover:bg-stone-50 ${
                  p === user.plan ? 'font-semibold text-orange-700' : 'text-stone-700'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        )}
      </td>
      <td className="py-3 px-3 text-sm text-stone-600">{formatDate(user.created_at)}</td>
      <td className="py-3 px-3 text-sm text-stone-500">{timeAgo(user.updated_at)}</td>
      <td className="py-3 px-3 text-sm text-stone-700 text-center">{user.recipes_count}</td>
      <td className="py-3 px-3 text-sm text-stone-700 text-center">{user.ingredients_count}</td>
      <td className="py-3 px-3 text-sm text-stone-700 text-center">{user.invoices_count}</td>
      <td className="py-3 px-3">
        <div className="flex items-center gap-1">
          <button
            onClick={handleFixPrices}
            disabled={fixing}
            className="text-stone-400 hover:text-red-600 disabled:opacity-50 transition-colors p-1"
            title="Corriger les prix sur-gonflés"
          >
            {fixing ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Wrench size={16} />
            )}
          </button>
          <button
            onClick={handleNormalize}
            disabled={normalizing}
            className="text-stone-400 hover:text-orange-600 disabled:opacity-50 transition-colors p-1"
            title="Normaliser les unités"
          >
            {normalizing ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <RefreshCw size={16} />
            )}
          </button>
        </div>
      </td>
    </tr>
  );
}

/* ------------------------------------------------------------------ */
/*  User Card (mobile)                                                 */
/* ------------------------------------------------------------------ */

function UserCard({ user }: { user: AdminUser }) {
  const [showPlanDropdown, setShowPlanDropdown] = useState(false);
  const updatePlan = useUpdateUserPlan();
  const normalizeUnits = useNormalizeUnits();
  const fixPrices = useFixInflatedPrices();
  const [normalizing, setNormalizing] = useState(false);
  const [fixing, setFixing] = useState(false);

  function handlePlanChange(plan: string) {
    setShowPlanDropdown(false);
    updatePlan.mutate(
      { id: user.id, plan },
      {
        onSuccess: () => toast.success(`Plan mis à jour → ${plan}`),
        onError: (err) => toast.error(err.message),
      },
    );
  }

  function handleNormalize() {
    setNormalizing(true);
    normalizeUnits.mutate(user.id, {
      onSuccess: (data) => {
        toast.success(
          `${data.ingredients_fixed} corrigé(s), ${data.recipes_recalculated} recalculée(s)`,
        );
        setNormalizing(false);
      },
      onError: (err) => {
        toast.error(err.message);
        setNormalizing(false);
      },
    });
  }

  function handleFixPrices() {
    setFixing(true);
    fixPrices.mutate(user.id, {
      onSuccess: (data) => {
        toast.success(
          `${data.prices_fixed} prix corrigé(s), ${data.recipes_recalculated} recalculée(s)`,
        );
        setFixing(false);
      },
      onError: (err) => {
        toast.error(err.message);
        setFixing(false);
      },
    });
  }

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-medium text-stone-900">{user.name}</p>
          <p className="text-xs text-stone-400">{user.owner_email}</p>
        </div>
        <div className="relative">
          <button
            onClick={() => setShowPlanDropdown(!showPlanDropdown)}
            className={`text-xs font-medium px-2.5 py-1 rounded-full ${planBadgeClass(user.plan)}`}
          >
            {user.plan}
          </button>
          {showPlanDropdown && (
            <div className="absolute right-0 z-10 mt-1 bg-white border border-stone-200 rounded-lg shadow-lg py-1 min-w-[100px]">
              {PLAN_OPTIONS.map((p) => (
                <button
                  key={p}
                  onClick={() => handlePlanChange(p)}
                  className={`block w-full text-left px-3 py-1.5 text-sm hover:bg-stone-50 ${
                    p === user.plan ? 'font-semibold text-orange-700' : 'text-stone-700'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="text-lg font-semibold text-stone-900">{user.recipes_count}</p>
          <p className="text-[10px] text-stone-400">Recettes</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-stone-900">{user.ingredients_count}</p>
          <p className="text-[10px] text-stone-400">Ingrédients</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-stone-900">{user.invoices_count}</p>
          <p className="text-[10px] text-stone-400">Factures</p>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-stone-400">
        <span>Inscrit le {formatDate(user.created_at)}</span>
        <span>{timeAgo(user.updated_at)}</span>
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleFixPrices}
          disabled={fixing}
          className="flex-1 flex items-center justify-center gap-2 text-sm text-stone-600 hover:text-red-700 border border-stone-200 rounded-lg py-2 disabled:opacity-50 transition-colors"
        >
          {fixing ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Wrench size={14} />
          )}
          Fix prix
        </button>
        <button
          onClick={handleNormalize}
          disabled={normalizing}
          className="flex-1 flex items-center justify-center gap-2 text-sm text-stone-600 hover:text-orange-700 border border-stone-200 rounded-lg py-2 disabled:opacity-50 transition-colors"
        >
          {normalizing ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <RefreshCw size={14} />
          )}
          Normaliser
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */

export default function Admin() {
  const { data: stats, isLoading: statsLoading } = useAdminStats();
  const { data: usersData, isLoading: usersLoading } = useAdminUsers();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-orange-50">
          <Shield size={22} className="text-orange-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-stone-900">Admin</h1>
          <p className="text-sm text-stone-500">Gestion des utilisateurs et statistiques</p>
        </div>
      </div>

      {/* Section 1 — Stats */}
      {statsLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="bg-white rounded-xl border border-stone-200 p-4 h-24 animate-pulse"
            />
          ))}
        </div>
      ) : stats ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard
            label="Restaurants"
            value={stats.total_restaurants}
            icon={Users}
            sub={`${stats.active_7d} actifs 7j · ${stats.active_30d} actifs 30j`}
          />
          <StatCard
            label="Plans"
            value={Object.values(stats.plans).reduce((a, b) => a + b, 0)}
            icon={TrendingUp}
            sub={Object.entries(stats.plans)
              .map(([k, v]) => `${v} ${k}`)
              .join(' · ')}
          />
          <StatCard
            label="Recettes"
            value={stats.total_recipes}
            icon={BookOpen}
            sub={`${stats.total_ingredients} ingrédients`}
          />
          <StatCard
            label="Factures"
            value={stats.total_invoices}
            icon={FileText}
            sub={`${stats.confirmed_invoices} confirmées`}
          />
        </div>
      ) : null}

      {/* Section 2 — Users table */}
      <div>
        <h2 className="text-lg font-semibold text-stone-900 mb-3">Utilisateurs</h2>

        {usersLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="bg-white rounded-xl border border-stone-200 p-4 h-20 animate-pulse"
              />
            ))}
          </div>
        ) : usersData?.users?.length ? (
          <>
            {/* Desktop table */}
            <div className="hidden md:block bg-white rounded-xl border border-stone-200 overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-stone-200 bg-stone-50/50">
                    <th className="text-left text-xs font-medium text-stone-500 px-3 py-2.5">
                      Restaurant
                    </th>
                    <th className="text-left text-xs font-medium text-stone-500 px-3 py-2.5">
                      Plan
                    </th>
                    <th className="text-left text-xs font-medium text-stone-500 px-3 py-2.5">
                      Inscrit le
                    </th>
                    <th className="text-left text-xs font-medium text-stone-500 px-3 py-2.5">
                      Dernière activité
                    </th>
                    <th className="text-center text-xs font-medium text-stone-500 px-3 py-2.5">
                      <UtensilsCrossed size={14} className="inline" />
                    </th>
                    <th className="text-center text-xs font-medium text-stone-500 px-3 py-2.5">
                      <BookOpen size={14} className="inline" />
                    </th>
                    <th className="text-center text-xs font-medium text-stone-500 px-3 py-2.5">
                      <FileText size={14} className="inline" />
                    </th>
                    <th className="text-xs font-medium text-stone-500 px-3 py-2.5"></th>
                  </tr>
                </thead>
                <tbody>
                  {usersData.users.map((user) => (
                    <UserRow key={user.id} user={user} />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="md:hidden space-y-3">
              {usersData.users.map((user) => (
                <UserCard key={user.id} user={user} />
              ))}
            </div>
          </>
        ) : (
          <p className="text-sm text-stone-400 text-center py-8">Aucun utilisateur</p>
        )}
      </div>
    </div>
  );
}
