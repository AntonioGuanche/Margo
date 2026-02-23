import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { SlidersHorizontal, Search, ChevronDown, ChevronRight } from 'lucide-react';
import { useRecipes } from '../hooks/useRecipes';
import { SkeletonList } from '../components/Skeleton';
import type { RecipeListItem } from '../hooks/useRecipes';

const STATUS_COLORS = {
  green: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  orange: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
  red: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
} as const;

const CATEGORY_ORDER = ['entrée', 'plat', 'dessert', 'boisson', 'autre'];

function groupByCategory(recipes: RecipeListItem[]) {
  const groups: Record<string, RecipeListItem[]> = {};
  for (const r of recipes) {
    const cat = r.category?.toLowerCase() || 'autre';
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(r);
  }
  // Sort by predefined order, unknowns at the end
  return Object.entries(groups).sort(([a], [b]) => {
    const ia = CATEGORY_ORDER.indexOf(a);
    const ib = CATEGORY_ORDER.indexOf(b);
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
  });
}

export default function SimulatorHome() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const { data, isLoading } = useRecipes(search || undefined);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const recipes = data?.items ?? [];
  const grouped = groupByCategory(recipes);

  const toggleCategory = (cat: string) => {
    setCollapsed((prev) => ({ ...prev, [cat]: !prev[cat] }));
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-stone-900 flex items-center gap-2">
          <SlidersHorizontal size={22} className="text-orange-700" />
          Simulateur — Que se passe-t-il si...
        </h2>
        <p className="text-sm text-stone-500 mt-1">
          Sélectionne un plat pour simuler l'impact d'un changement de prix ou de portion.
        </p>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full border border-stone-300 rounded-lg pl-10 pr-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
          placeholder="Rechercher un plat..."
        />
      </div>

      {/* List grouped by category */}
      {isLoading ? (
        <SkeletonList count={5} />
      ) : recipes.length === 0 ? (
        <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
          <SlidersHorizontal size={40} className="mx-auto text-stone-300 mb-3" />
          <p className="text-stone-600 font-medium mb-1">
            {search ? `Aucun plat trouvé pour « ${search} »` : 'Aucune recette'}
          </p>
          <p className="text-sm text-stone-400">
            {search ? '' : 'Crée des recettes pour utiliser le simulateur.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {grouped.map(([category, items]) => {
            const isCollapsed = collapsed[category] ?? false;
            const avgCost =
              items.filter((r) => r.food_cost_percent != null).length > 0
                ? items
                    .filter((r) => r.food_cost_percent != null)
                    .reduce((sum, r) => sum + (r.food_cost_percent ?? 0), 0) /
                  items.filter((r) => r.food_cost_percent != null).length
                : null;

            return (
              <div key={category}>
                <button
                  onClick={() => toggleCategory(category)}
                  className="flex items-center gap-2 w-full text-left mb-2"
                >
                  {isCollapsed ? (
                    <ChevronRight size={14} className="text-stone-400" />
                  ) : (
                    <ChevronDown size={14} className="text-stone-400" />
                  )}
                  <span className="text-xs font-semibold text-stone-500 uppercase tracking-wide">
                    {category} ({items.length})
                  </span>
                  {avgCost != null && (
                    <span className="text-xs text-stone-400">
                      — moy. {avgCost.toFixed(1)}%
                    </span>
                  )}
                </button>

                {!isCollapsed && (
                  <div className="space-y-2">
                    {items.map((recipe) => {
                      const colors = STATUS_COLORS[recipe.margin_status];
                      return (
                        <button
                          key={recipe.id}
                          onClick={() => navigate(`/recipes/${recipe.id}/simulate`)}
                          className="w-full bg-white rounded-xl border border-stone-200 px-4 py-3 flex items-center justify-between hover:border-orange-300 transition-colors text-left"
                        >
                          <div className="min-w-0 flex-1">
                            <div className="font-medium text-stone-900 truncate">
                              {recipe.name}
                            </div>
                            <div className="text-sm text-stone-500 mt-0.5">
                              {recipe.selling_price.toFixed(2)} €
                            </div>
                          </div>
                          <div className="flex items-center gap-2 ml-2 shrink-0">
                            {recipe.food_cost_percent != null && (
                              <span className={`text-sm font-semibold ${colors.text}`}>
                                {recipe.food_cost_percent.toFixed(1)}%
                              </span>
                            )}
                            <span
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}
                            >
                              <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
