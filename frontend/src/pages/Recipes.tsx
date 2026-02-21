import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, ChefHat } from 'lucide-react';
import { useRecipes } from '../hooks/useRecipes';
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

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-stone-900 flex items-center gap-2">
          <ChefHat size={22} className="text-orange-700" />
          Recettes
        </h2>
        <button
          onClick={() => navigate('/recipes/new')}
          className="bg-orange-700 text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-orange-800 transition-colors flex items-center gap-1"
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
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-700" />
        </div>
      ) : !data?.items.length ? (
        <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
          <p className="text-stone-500">
            {search
              ? `Aucune recette trouvée pour "${search}"`
              : 'Aucune recette. Commencez par en ajouter une !'}
          </p>
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
    </div>
  );
}
