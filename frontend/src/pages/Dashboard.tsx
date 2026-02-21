import { LayoutDashboard } from 'lucide-react';

export default function Dashboard() {
  return (
    <div>
      <h2 className="text-xl font-semibold text-stone-900 mb-4 flex items-center gap-2">
        <LayoutDashboard size={22} className="text-orange-700" />
        Dashboard
      </h2>
      <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
        <p className="text-stone-500">
          Le dashboard arrivera au Sprint 2 avec les recettes et le calcul de food cost.
        </p>
      </div>
    </div>
  );
}
