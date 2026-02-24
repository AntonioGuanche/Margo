import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, BookOpen, Camera, ChevronDown, ChevronRight, Pencil, FileText } from 'lucide-react';
import { useRecipes } from '../hooks/useRecipes';
import { usePlanInfo } from '../hooks/useBilling';
import { SkeletonList } from '../components/Skeleton';
import UpgradeModal from '../components/UpgradeModal';
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
  return Object.entries(groups).sort(([a], [b]) => {
    const ia = CATEGORY_ORDER.indexOf(a);
    const ib = CATEGORY_ORDER.indexOf(b);
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
  });
}

function RecipeCard({ recipe, onClick }: { recipe: RecipeListItem; onClick: () => void }) {
  const colors = STATUS_COLORS[recipe.margin_status];
  return (
    <button
      onClick={onClick}
      className="w-full bg-white rounded-xl border border-stone-200 px-4 py-3 flex items-center justify-between hover:border-stone-300 transition-colors text-left"
    >
      <div className="min-w-0 flex-1">
        <div className="font-medium text-stone-900 truncate flex items-center gap-1.5">
          {recipe.name}
          <span className={`text-xs px-1.5 py-0.5 rounded-full ${
            recipe.is_homemade
              ? 'bg-orange-50 text-orange-700'
              : 'bg-stone-100 text-stone-500'
          }`}>
            {recipe.is_homemade ? 'Maison' : 'Acheté'}
          </span>
        </div>
        <div className="text-sm text-stone-500 flex gap-3 mt-0.5">
          <span>{recipe.selling_price.toFixed(2)} €</span>
        </div>
      </div>
      <div className="flex items-center gap-2 ml-2 shrink-0">
        {recipe.food_cost_percent != null && (
          <span className={`text-sm font-semibold ${colors.text}`}>
            {recipe.food_cost_percent.toFixed(1)}%
          </span>
        )}
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
        </span>
      </div>
    </button>
  );
}

export default function Recipes() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const { data, isLoading } = useRecipes(search || undefined);
  const { data: planInfo } = usePlanInfo();
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [showAddMenu, setShowAddMenu] = useState(false);
  const addMenuRef = useRef<HTMLDivElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const atLimit =
    planInfo?.max_recipes !== null &&
    planInfo?.max_recipes !== undefined &&
    planInfo.current_recipes >= planInfo.max_recipes;

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (addMenuRef.current && !addMenuRef.current.contains(e.target as Node)) {
        setShowAddMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function handleMenuFile(file: File) {
    navigate('/onboarding', { state: { file } });
  }

  const recipes = data?.items ?? [];
  const grouped = groupByCategory(recipes);

  const toggleCategory = (cat: string) => {
    setCollapsed((prev) => ({ ...prev, [cat]: !prev[cat] }));
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-semibold text-stone-900 flex items-center gap-2">
            <BookOpen size={22} className="text-orange-700" />
            Ma carte
          </h2>
          {planInfo?.max_recipes !== null && planInfo?.max_recipes !== undefined && (
            <span className="text-xs text-stone-400 bg-stone-100 px-2 py-0.5 rounded-full">
              {planInfo.current_recipes}/{planInfo.max_recipes}
            </span>
          )}
        </div>
        <div className="relative" ref={addMenuRef}>
          <button
            onClick={() => {
              if (atLimit) {
                setShowUpgrade(true);
                return;
              }
              setShowAddMenu(!showAddMenu);
            }}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1 ${
              atLimit
                ? 'bg-stone-200 text-stone-400 cursor-not-allowed'
                : 'bg-orange-700 text-white hover:bg-orange-800'
            }`}
          >
            <Plus size={16} />
            Ajouter
            {!atLimit && <ChevronDown size={14} />}
          </button>

          {showAddMenu && (
            <div className="absolute right-0 top-full mt-1 w-64 bg-white rounded-xl border border-stone-200 shadow-lg z-50 overflow-hidden">
              <button
                onClick={() => { setShowAddMenu(false); navigate('/recipes/new'); }}
                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-stone-50 text-left"
              >
                <Pencil size={18} className="text-stone-500" />
                <div>
                  <p className="text-sm font-medium text-stone-900">Ajouter manuellement</p>
                  <p className="text-xs text-stone-500">Créer un plat avec prix et ingrédients</p>
                </div>
              </button>
              <button
                onClick={() => { setShowAddMenu(false); cameraRef.current?.click(); }}
                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-stone-50 text-left border-t border-stone-100"
              >
                <Camera size={18} className="text-stone-500" />
                <div>
                  <p className="text-sm font-medium text-stone-900">Photographier ma carte</p>
                  <p className="text-xs text-stone-500">L'IA extraira les plats et prix</p>
                </div>
              </button>
              <button
                onClick={() => { setShowAddMenu(false); fileRef.current?.click(); }}
                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-stone-50 text-left border-t border-stone-100"
              >
                <FileText size={18} className="text-stone-500" />
                <div>
                  <p className="text-sm font-medium text-stone-900">Importer un fichier</p>
                  <p className="text-xs text-stone-500">PDF ou image de votre carte</p>
                </div>
              </button>
            </div>
          )}
        </div>

        {/* Hidden inputs for camera & file picker */}
        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleMenuFile(e.target.files[0])}
        />
        <input
          ref={fileRef}
          type="file"
          accept=".jpg,.jpeg,.png,.webp,.pdf"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleMenuFile(e.target.files[0])}
        />
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
          <BookOpen size={40} className="mx-auto text-stone-300 mb-3" />
          <p className="text-stone-600 font-medium mb-1">
            {search
              ? `Aucun plat trouvé pour « ${search} »`
              : 'Aucun plat sur ta carte'}
          </p>
          {!search && (
            <>
              <p className="text-sm text-stone-400 mb-4">
                Commence par photographier ta carte !
              </p>
              <button
                onClick={() => navigate('/onboarding')}
                className="bg-orange-700 text-white px-4 py-2.5 rounded-xl text-sm font-medium hover:bg-orange-800 transition-colors inline-flex items-center gap-2"
              >
                <Camera size={16} />
                Photographier ma carte
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {grouped.map(([category, items], idx) => {
            const isCollapsed = collapsed[category] ?? (idx > 0);
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
                    {items.map((recipe) => (
                      <RecipeCard
                        key={recipe.id}
                        recipe={recipe}
                        onClick={() => navigate(`/recipes/${recipe.id}`)}
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
          <p className="text-sm text-stone-400 text-center pt-2">
            {data?.total ?? 0} plat{(data?.total ?? 0) > 1 ? 's' : ''}
          </p>
        </div>
      )}

      <UpgradeModal
        show={showUpgrade}
        onClose={() => setShowUpgrade(false)}
        message="Tu as atteint la limite de 5 recettes pour le plan gratuit. Passe au Pro pour un accès illimité."
      />
    </div>
  );
}
