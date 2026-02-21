import { useNavigate } from 'react-router-dom';
import { LayoutDashboard, ChefHat, TrendingUp, Camera, FileDown } from 'lucide-react';
import { useDashboard } from '../hooks/useRecipes';
import type { RecipeListItem } from '../hooks/useRecipes';

const STATUS_COLORS = {
  green: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500', border: 'border-emerald-200' },
  orange: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500', border: 'border-amber-200' },
  red: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500', border: 'border-red-200' },
} as const;

function StatusBadge({ status }: { status: 'green' | 'orange' | 'red' }) {
  const colors = STATUS_COLORS[status];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
      {status === 'green' ? 'OK' : status === 'orange' ? 'Attention' : 'Critique'}
    </span>
  );
}

function RecipeRow({ recipe, onClick }: { recipe: RecipeListItem; onClick: () => void }) {
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
      <div className="flex items-center gap-3 ml-2 shrink-0">
        {recipe.food_cost_percent != null && (
          <span className={`text-sm font-semibold ${STATUS_COLORS[recipe.margin_status].text}`}>
            {recipe.food_cost_percent.toFixed(1)}%
          </span>
        )}
        <StatusBadge status={recipe.margin_status} />
      </div>
    </button>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { data, isLoading } = useDashboard();

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-700" />
      </div>
    );
  }

  if (!data || data.total_recipes === 0) {
    return (
      <div>
        <h2 className="text-xl font-semibold text-stone-900 mb-4 flex items-center gap-2">
          <LayoutDashboard size={22} className="text-orange-700" />
          Dashboard
        </h2>
        <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
          <ChefHat size={48} className="mx-auto text-stone-300 mb-4" />
          <p className="text-stone-500 mb-4">
            Ajoute ta première recette pour voir ton food cost
          </p>
          <button
            onClick={() => navigate('/onboarding')}
            className="w-full bg-orange-700 text-white px-4 py-4 rounded-xl text-lg font-medium hover:bg-orange-800 transition-colors flex items-center justify-center gap-2 mb-3"
          >
            <Camera size={24} />
            Commencer — Photographier ma carte
          </button>
          <button
            onClick={() => navigate('/recipes/new')}
            className="text-sm text-orange-700 hover:underline"
          >
            Ou créer une recette manuellement
          </button>
        </div>
      </div>
    );
  }

  const avgStatus =
    data.average_food_cost_percent === null
      ? 'green'
      : data.average_food_cost_percent < 30
        ? 'green'
        : data.average_food_cost_percent <= 35
          ? 'orange'
          : 'red';

  return (
    <div>
      <h2 className="text-xl font-semibold text-stone-900 mb-4 flex items-center gap-2">
        <LayoutDashboard size={22} className="text-orange-700" />
        Dashboard
      </h2>

      {/* Big food cost number */}
      <div className={`rounded-xl border p-6 mb-4 text-center ${STATUS_COLORS[avgStatus].bg} ${STATUS_COLORS[avgStatus].border}`}>
        <p className="text-sm text-stone-500 mb-1">Food cost moyen</p>
        <p className={`text-4xl font-bold ${STATUS_COLORS[avgStatus].text}`}>
          {data.average_food_cost_percent !== null
            ? `${data.average_food_cost_percent.toFixed(1)}%`
            : '—'}
        </p>
        <div className="flex items-center justify-center gap-1 mt-2">
          <TrendingUp size={14} className="text-stone-400" />
          <span className="text-xs text-stone-500">{data.total_recipes} recette{data.total_recipes > 1 ? 's' : ''}</span>
        </div>
      </div>

      {/* Status counters */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-center">
          <p className="text-2xl font-bold text-emerald-700">{data.recipes_green}</p>
          <p className="text-xs text-emerald-600">OK</p>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-center">
          <p className="text-2xl font-bold text-amber-700">{data.recipes_orange}</p>
          <p className="text-xs text-amber-600">Attention</p>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-center">
          <p className="text-2xl font-bold text-red-700">{data.recipes_red}</p>
          <p className="text-xs text-red-600">Critique</p>
        </div>
      </div>

      {/* Import invoice CTA */}
      <button
        onClick={() => navigate('/invoices/upload')}
        className="w-full bg-stone-100 border border-stone-200 rounded-xl px-4 py-3 flex items-center gap-3 hover:bg-stone-200 transition-colors mb-4"
      >
        <FileDown size={20} className="text-orange-700" />
        <span className="text-sm font-medium text-stone-700">Importer une facture</span>
      </button>

      {/* Recipe list sorted worst first */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-stone-500 uppercase tracking-wide">
          Plats par food cost
        </h3>
        {data.recipes.map((recipe) => (
          <RecipeRow
            key={recipe.id}
            recipe={recipe}
            onClick={() => navigate(`/recipes/${recipe.id}`)}
          />
        ))}
      </div>
    </div>
  );
}
