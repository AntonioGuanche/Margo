import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { UtensilsCrossed, LayoutDashboard, ChefHat, FileText, LogOut } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useInvoices } from '../hooks/useInvoices';

export default function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const { data: invoicesData } = useInvoices('pending_review');
  const pendingCount = invoicesData?.total ?? 0;

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="min-h-screen bg-stone-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-stone-200 px-4 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold text-orange-700">Margó</h1>
        <button
          onClick={handleLogout}
          className="text-stone-500 hover:text-stone-700 p-2"
          title="Déconnexion"
        >
          <LogOut size={20} />
        </button>
      </header>

      {/* Content */}
      <main className="flex-1 p-4 pb-20 max-w-2xl mx-auto w-full">
        <Outlet />
      </main>

      {/* Bottom nav — mobile */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-stone-200 flex justify-around py-2 md:hidden">
        <NavLink
          to="/"
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
          <span>Ingrédients</span>
        </NavLink>
      </nav>
    </div>
  );
}
