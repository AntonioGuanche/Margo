import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, ChefHat, Camera } from 'lucide-react';
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

function RecipeCard({ recipe, onClick }: { recipe: RecipeListItem; onClick: () => void }) {
  const colors = STATUS_COLORS[recipe.margin_status];
  return (
    <button
      onClick={onClick}
      className="w-full bg-white rounded-xl border border-stone-200 px-4 py-3 flex items-center justify-between hover:border-stone-300 transition-colors text-left"
    >
      <div className="min-w-0 flex-1">
        <div className="font-medium text-stone-900 truncate">{recipe.name}</div>
        <div className="text-sm text-stone-500 flex gap-3 mt-0.5">
          {recipe.category && <span>{recipe.category}</span>}
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

  const atLimit =
    planInfo?.max_recipes !== null &&
    planInfo?.max_recipes !== undefined &&
    planInfo.current_recipes >= planInfo.max_recipes;

  function handleAdd() {
    if (atLimit) {
      setShowUpgrade(true);
      return;
    }
    navigate('/recipes/new');
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-semibold text-stone-900 flex items-center gap-2">
            <ChefHat size={22} className="text-orange-700" />
            Recettes
          </h2>
          {planInfo?.max_recipes !== null && planInfo?.max_recipes !== undefined && (
            <span className="text-xs text-stone-400 bg-stone-100 px-2 py-0.5 rounded-full">
              {planInfo.current_recipes}/{planInfo.max_recipes}
            </span>
          )}
        </div>
        <button
          onClick={handleAdd}
          disabled={atLimit}
          className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1 ${
            atLimit
              ? 'bg-stone-200 text-stone-400 cursor-not-allowed'
              : 'bg-orange-700 text-white hover:bg-orange-800'
          }`}
        >
          <Plus size={16} />
          Ajouter
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full border border-stone-300 rounded-lg pl-10 pr-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
          placeholder="Rechercher une recette..."
        />
      </div>

      {/* List */}
      {isLoading ? (
        <SkeletonList count={5} />
      ) : !data?.items.length ? (
        <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
          <ChefHat size={40} className="mx-auto text-stone-300 mb-3" />
          <p className="text-stone-600 font-medium mb-1">
            {search
              ? `Aucune recette trouvée pour « ${search} »`
              : 'Aucune recette'}
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
        <div className="space-y-2">
          {data.items.map((recipe) => (
            <RecipeCard
              key={recipe.id}
              recipe={recipe}
              onClick={() => navigate(`/recipes/${recipe.id}`)}
            />
          ))}
          <p className="text-sm text-stone-400 text-center pt-2">
            {data.total} recette{data.total > 1 ? 's' : ''}
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
