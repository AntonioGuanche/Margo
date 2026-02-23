import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
  UtensilsCrossed,
  LayoutDashboard,
  ChefHat,
  FileText,
  LogOut,
  Bell,
  Settings,
  SlidersHorizontal,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useInvoices } from '../hooks/useInvoices';
import { useAlertCount } from '../hooks/useAlerts';

/* ------------------------------------------------------------------ */
/*  Sidebar link (desktop)                                             */
/* ------------------------------------------------------------------ */

function SidebarLink({
  to,
  icon: Icon,
  label,
  badge,
  end,
}: {
  to: string;
  icon: React.ComponentType<{ size?: number }>;
  label: string;
  badge?: number;
  end?: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? 'bg-orange-50 text-orange-700'
            : 'text-stone-600 hover:bg-stone-50 hover:text-stone-900'
        }`
      }
    >
      <Icon size={20} />
      <span className="flex-1">{label}</span>
      {badge != null && badge > 0 && (
        <span className="bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
          {badge > 99 ? '99+' : badge}
        </span>
      )}
    </NavLink>
  );
}

/* ------------------------------------------------------------------ */
/*  Layout                                                             */
/* ------------------------------------------------------------------ */

export default function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const { data: invoicesData } = useInvoices('pending_review');
  const pendingCount = invoicesData?.total ?? 0;
  const { data: alertCount } = useAlertCount();
  const unreadAlerts = alertCount?.unread_count ?? 0;

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="min-h-screen bg-stone-50 flex flex-col">
      {/* ---- Header (full width) ---- */}
      <header className="bg-white border-b border-stone-200 px-4 py-3 flex items-center justify-between">
        <NavLink
          to="/"
          className="text-xl font-bold text-orange-700 hover:text-orange-800 transition-colors"
        >
          Marg\u00f3
        </NavLink>

        <div className="flex items-center gap-1">
          {/* Alerts & Settings icons — mobile only (sidebar has them on desktop) */}
          <button
            onClick={() => navigate('/alerts')}
            className="relative text-stone-500 hover:text-stone-700 p-2 md:hidden"
            title="Alertes"
          >
            <Bell size={20} />
            {unreadAlerts > 0 && (
              <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
                {unreadAlerts > 9 ? '9+' : unreadAlerts}
              </span>
            )}
          </button>
          <button
            onClick={() => navigate('/settings')}
            className="text-stone-500 hover:text-stone-700 p-2 md:hidden"
            title="Param\u00e8tres"
          >
            <Settings size={20} />
          </button>
          <button
            onClick={handleLogout}
            className="text-stone-500 hover:text-stone-700 p-2"
            title="D\u00e9connexion"
          >
            <LogOut size={20} />
          </button>
        </div>
      </header>

      {/* ---- Body: sidebar (desktop) + content ---- */}
      <div className="flex flex-1">
        {/* Sidebar — desktop only */}
        <aside className="hidden md:flex md:flex-col md:w-[220px] bg-white border-r border-stone-200 p-3 shrink-0">
          <nav className="flex flex-col gap-1 flex-1">
            <SidebarLink to="/" icon={LayoutDashboard} label="Dashboard" end />
            <SidebarLink to="/recipes" icon={ChefHat} label="Recettes" />
            <SidebarLink to="/ingredients" icon={UtensilsCrossed} label="Ingr\u00e9dients" />
            <SidebarLink
              to="/invoices"
              icon={FileText}
              label="Factures"
              badge={pendingCount}
            />
            <SidebarLink to="/simulator" icon={SlidersHorizontal} label="Simulateur" />
            <SidebarLink to="/alerts" icon={Bell} label="Alertes" badge={unreadAlerts} />
          </nav>

          {/* Settings pinned to bottom */}
          <div className="border-t border-stone-200 pt-2 mt-2">
            <SidebarLink to="/settings" icon={Settings} label="Param\u00e8tres" />
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 p-4 pb-20 md:pb-6 max-w-4xl mx-auto w-full">
          <Outlet />
        </main>
      </div>

      {/* ---- Bottom nav — mobile only ---- */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-stone-200 flex justify-around py-2 md:hidden">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `flex flex-col items-center text-xs ${isActive ? 'text-orange-700' : 'text-stone-400'}`
          }
        >
          <LayoutDashboard size={20} />
          <span>Dashboard</span>
        </NavLink>
        <NavLink
          to="/recipes"
          className={({ isActive }) =>
            `flex flex-col items-center text-xs ${isActive ? 'text-orange-700' : 'text-stone-400'}`
          }
        >
          <ChefHat size={20} />
          <span>Recettes</span>
        </NavLink>
        <NavLink
          to="/invoices"
          className={({ isActive }) =>
            `flex flex-col items-center text-xs relative ${isActive ? 'text-orange-700' : 'text-stone-400'}`
          }
        >
          <div className="relative">
            <FileText size={20} />
            {pendingCount > 0 && (
              <span className="absolute -top-1.5 -right-2 bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
                {pendingCount > 9 ? '9+' : pendingCount}
              </span>
            )}
          </div>
          <span>Factures</span>
        </NavLink>
        <NavLink
          to="/ingredients"
          className={({ isActive }) =>
            `flex flex-col items-center text-xs ${isActive ? 'text-orange-700' : 'text-stone-400'}`
          }
        >
          <UtensilsCrossed size={20} />
          <span>Ingr\u00e9dients</span>
        </NavLink>
        <NavLink
          to="/simulator"
          className={({ isActive }) =>
            `flex flex-col items-center text-xs ${isActive ? 'text-orange-700' : 'text-stone-400'}`
          }
        >
          <SlidersHorizontal size={20} />
          <span>Simuler</span>
        </NavLink>
      </nav>
    </div>
  );
}
