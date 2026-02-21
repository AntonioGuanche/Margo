import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react';
import { useRecipe, useDeleteRecipe } from '../hooks/useRecipes';

const STATUS_COLORS = {
  green: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500', border: 'border-emerald-200' },
  orange: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500', border: 'border-amber-200' },
  red: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500', border: 'border-red-200' },
} as const;

export default function RecipeDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: recipe, isLoading } = useRecipe(id ? parseInt(id) : null);
  const deleteMutation = useDeleteRecipe();

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-700" />
      </div>
    );
  }

  if (!recipe) {
    return (
      <div className="text-center py-12">
        <p className="text-stone-500">Recette introuvable</p>
        <button onClick={() => navigate('/recipes')} className="text-orange-700 hover:underline text-sm mt-2">
          Retour aux recettes
        </button>
      </div>
    );
  }

  function handleDelete() {
    if (!recipe || !confirm(`Supprimer "${recipe.name}" ?`)) return;
    deleteMutation.mutate(recipe.id, {
      onSuccess: () => navigate('/recipes'),
    });
  }

  const colors = STATUS_COLORS[recipe.margin_status];

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
      <div className={`rounded-xl border p-4 mb-4 ${colors.bg} ${colors.border}`}>
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-xl font-bold text-stone-900">{recipe.name}</h2>
            {recipe.category && (
              <span className="text-sm text-stone-500">{recipe.category}</span>
            )}
          </div>
          <div className="flex gap-1">
            <button
              onClick={() => navigate(`/recipes/${recipe.id}/edit`)}
              className="p-2 text-stone-500 hover:text-orange-700 transition-colors"
              title="Modifier"
            >
              <Pencil size={18} />
            </button>
            <button
              onClick={handleDelete}
              className="p-2 text-stone-500 hover:text-red-600 transition-colors"
              title="Supprimer"
            >
              <Trash2 size={18} />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mt-4">
          <div>
            <p className="text-xs text-stone-500">Prix de vente</p>
            <p className="text-lg font-semibold text-stone-900">
              {recipe.selling_price.toFixed(2)} €
            </p>
          </div>
          <div>
            <p className="text-xs text-stone-500">Food cost</p>
            <p className={`text-lg font-semibold ${colors.text}`}>
              {recipe.food_cost_percent != null
                ? `${recipe.food_cost_percent.toFixed(1)}%`
                : '—'}
            </p>
          </div>
          <div>
            <p className="text-xs text-stone-500">Coût total</p>
            <p className="text-lg font-semibold text-stone-900">
              {recipe.food_cost != null ? `${recipe.food_cost.toFixed(2)} €` : '—'}
            </p>
          </div>
        </div>
      </div>

      {/* Ingredients */}
      <h3 className="text-sm font-medium text-stone-500 uppercase tracking-wide mb-2">
        Ingrédients ({recipe.ingredients.length})
      </h3>
      <div className="bg-white rounded-xl border border-stone-200 divide-y divide-stone-100 overflow-hidden">
        {recipe.ingredients.map((ri) => (
          <div key={ri.id} className="px-4 py-3 flex items-center justify-between">
            <div>
              <span className="font-medium text-stone-900">{ri.ingredient_name}</span>
              <span className="text-sm text-stone-500 ml-2">
                {ri.quantity} {ri.unit}
              </span>
            </div>
            <div className="text-right">
              {ri.unit_cost != null && (
                <p className="text-xs text-stone-400">
                  {ri.unit_cost.toFixed(2)} €/{ri.unit}
                </p>
              )}
              <p className="text-sm font-medium text-stone-700">
                {ri.line_cost != null ? `${ri.line_cost.toFixed(2)} €` : '—'}
              </p>
            </div>
          </div>
        ))}

        {/* Total */}
        <div className="px-4 py-3 flex items-center justify-between bg-stone-50">
          <span className="font-semibold text-stone-900">Total</span>
          <span className="font-semibold text-stone-900">
            {recipe.food_cost != null ? `${recipe.food_cost.toFixed(2)} €` : '—'}
          </span>
        </div>
      </div>
    </div>
  );
}
