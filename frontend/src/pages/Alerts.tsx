import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Bell, CheckCheck, TrendingUp, ChefHat, PartyPopper } from 'lucide-react';
import { useAlerts, useMarkAlertRead, useMarkAllRead } from '../hooks/useAlerts';
import { SkeletonList } from '../components/Skeleton';
import type { AlertItem } from '../types';

function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "à l'instant";
  if (diffMin < 60) return `il y a ${diffMin} min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `il y a ${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 7) return `il y a ${diffD}j`;
  return date.toLocaleDateString('fr-BE', { day: '2-digit', month: 'short' });
}

const SEVERITY_STYLES = {
  warning: {
    border: 'border-amber-300',
    bg: 'bg-amber-50',
    icon: '🟠',
  },
  critical: {
    border: 'border-red-300',
    bg: 'bg-red-50',
    icon: '🔴',
  },
} as const;

function AlertRow({
  alert,
  onRead,
  onClick,
}: {
  alert: AlertItem;
  onRead: (id: number) => void;
  onClick: (alert: AlertItem) => void;
}) {
  const style = SEVERITY_STYLES[alert.severity as keyof typeof SEVERITY_STYLES] ?? SEVERITY_STYLES.warning;

  return (
    <button
      onClick={() => {
        if (!alert.is_read) onRead(alert.id);
        onClick(alert);
      }}
      className={`w-full text-left rounded-xl border px-4 py-3 transition-colors ${style.border} ${style.bg} ${
        alert.is_read ? 'opacity-60' : ''
      } hover:opacity-90`}
    >
      <div className="flex items-start gap-3">
        <span className="text-lg mt-0.5">{style.icon}</span>
        <div className="flex-1 min-w-0">
          <p className={`text-sm text-stone-900 ${alert.is_read ? '' : 'font-semibold'}`}>
            {alert.message}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-stone-400">{timeAgo(alert.created_at)}</span>
            {alert.recipe_id && (
              <span className="text-xs text-orange-600 flex items-center gap-0.5">
                <ChefHat size={10} />
                Simuler
              </span>
            )}
            {alert.ingredient_id && !alert.recipe_id && (
              <span className="text-xs text-stone-500 flex items-center gap-0.5">
                <TrendingUp size={10} />
                Voir
              </span>
            )}
          </div>
        </div>
        {!alert.is_read && (
          <span className="w-2 h-2 rounded-full bg-orange-500 mt-2 shrink-0" />
        )}
      </div>
    </button>
  );
}

export default function Alerts() {
  const navigate = useNavigate();
  const { data, isLoading } = useAlerts();
  const markRead = useMarkAlertRead();
  const markAllRead = useMarkAllRead();

  function handleClick(alert: AlertItem) {
    if (alert.recipe_id) {
      navigate(`/recipes/${alert.recipe_id}/simulate`);
    } else if (alert.ingredient_id) {
      navigate('/ingredients');
    }
  }

  if (isLoading) {
    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-stone-900 flex items-center gap-2">
            <Bell size={22} className="text-orange-700" />
            Alertes
          </h2>
        </div>
        <SkeletonList count={3} />
      </div>
    );
  }

  return (
    <div>
      {/* Back button */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-stone-500 hover:text-stone-700 text-sm mb-4"
      >
        <ArrowLeft size={16} />
        Retour
      </button>

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-stone-900 flex items-center gap-2">
          <Bell size={22} className="text-orange-700" />
          Alertes
        </h2>
        {data && data.unread_count > 0 && (
          <button
            onClick={() => markAllRead.mutate()}
            disabled={markAllRead.isPending}
            className="text-sm text-orange-700 hover:text-orange-800 flex items-center gap-1"
          >
            <CheckCheck size={16} />
            Tout marquer comme lu
          </button>
        )}
      </div>

      {!data?.items.length ? (
        <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
          <PartyPopper size={40} className="mx-auto text-stone-300 mb-3" />
          <p className="text-stone-600 font-medium mb-1">Aucune alerte. Tout va bien !</p>
          <p className="text-sm text-stone-400">
            Les alertes apparaissent quand un prix fournisseur augmente significativement.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {data.items.map((alert) => (
            <AlertRow
              key={alert.id}
              alert={alert}
              onRead={(id) => markRead.mutate(id)}
              onClick={handleClick}
            />
          ))}
          <p className="text-sm text-stone-400 text-center pt-2">
            {data.total} alerte{data.total > 1 ? 's' : ''}
            {data.unread_count > 0 && ` · ${data.unread_count} non lue${data.unread_count > 1 ? 's' : ''}`}
          </p>
        </div>
      )}
    </div>
  );
}
