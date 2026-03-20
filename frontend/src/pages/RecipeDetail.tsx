import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { ArrowLeft, Pencil, Trash2, SlidersHorizontal, X } from 'lucide-react';
import { useRecipe, useDeleteRecipe, useRemoveRecipeIngredient } from '../hooks/useRecipes';
import ConfirmModal from '../components/ConfirmModal';
import { SkeletonList } from '../components/Skeleton';
import { STATUS_COLORS } from '../utils/colors';

export default function RecipeDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: recipe, isLoading } = useRecipe(id ? parseInt(id) : null);
  const deleteMutation = useDeleteRecipe();
  const removeIngredient = useRemoveRecipeIngredient();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);
  const [ingredientToRemove, setIngredientToRemove] = useState<{
    id: number;
    ingredient_id: number;
    ingredient_name: string;
  } | null>(null);

  if (isLoading) {
    return <SkeletonList count={4} />;
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
    if (!recipe) return;
    deleteMutation.mutate(recipe.id, {
      onSuccess: () => {
        toast.success('Recette supprimée');
        navigate('/recipes');
      },
      onError: (err) => toast.error(err.message),
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
              onClick={() => navigate(`/recipes/${recipe.id}/simulate`)}
              className="p-2 text-stone-500 hover:text-orange-700 transition-colors"
              title="Simuler"
            >
              <SlidersHorizontal size={18} />
            </button>
            <button
              onClick={() => navigate(`/recipes/${recipe.id}/edit`)}
              className="p-2 text-stone-500 hover:text-orange-700 transition-colors"
              title="Modifier"
            >
              <Pencil size={18} />
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
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
          <div key={ri.id} className="px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-medium text-stone-900">{ri.ingredient_name}</span>
                <span className="text-sm text-stone-500">
                  {ri.quantity} {ri.unit}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  {ri.unit_cost != null ? (
                    <p className="text-sm font-medium text-stone-700">
                      {ri.line_cost != null ? `${ri.line_cost.toFixed(2)} €` : '—'}
                    </p>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600 bg-amber-50 px-2 py-1 rounded-full">
                      <span className="w-1.5 h-1.5 bg-amber-500 rounded-full" />
                      Prix manquant
                    </span>
                  )}
                </div>
                <button
                  onClick={() => {
                    setIngredientToRemove(ri);
                    setShowRemoveConfirm(true);
                  }}
                  className="p-1 text-stone-300 hover:text-red-500 transition-colors"
                  title="Retirer de la recette"
                >
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* Calculation detail */}
            {ri.unit_cost != null && (
              <div className="mt-1 text-xs text-stone-400 flex items-center gap-1 flex-wrap">
                <span>{ri.quantity} {ri.unit}</span>

                {ri.unit !== (ri.unit_cost_unit ?? ri.unit) && (
                  ri.conversion_ok !== false ? (
                    <span>→ {ri.converted_quantity} {ri.unit_cost_unit}</span>
                  ) : (
                    <span className="text-red-500 font-medium">
                      ({ri.unit} ≠ {ri.unit_cost_unit})
                    </span>
                  )
                )}

                <span>× {ri.unit_cost.toFixed(2)} €/{ri.unit_cost_unit}</span>
                {ri.line_cost != null && (
                  <span className="font-medium text-stone-600">= {ri.line_cost.toFixed(2)} €</span>
                )}
                {ri.supplier_name && (
                  <span className="text-stone-300">— {ri.supplier_name}</span>
                )}
              </div>
            )}

            {/* Incompatible unit warning */}
            {ri.conversion_ok === false && (
              <div className="mt-1.5 px-2 py-1.5 bg-red-50 border border-red-100 rounded text-xs text-red-600">
                L'unité « {ri.unit} » n'est pas convertible vers « {ri.unit_cost_unit} ».
                Modifie la recette pour corriger (ex: remplace « {ri.unit} » par « cl » ou « l »).
              </div>
            )}
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

      {/* Remove ingredient confirmation */}
      {showRemoveConfirm && ingredientToRemove && recipe && (
        <ConfirmModal
          title={`Retirer « ${ingredientToRemove.ingredient_name} » ?`}
          message={`L'ingrédient sera retiré de la recette « ${recipe.name} ». Le food cost sera recalculé.`}
          onConfirm={() => {
            removeIngredient.mutate(
              { recipeId: recipe.id, ingredientId: ingredientToRemove.ingredient_id },
              {
                onSuccess: () => {
                  toast.success('Ingrédient retiré');
                  setShowRemoveConfirm(false);
                  setIngredientToRemove(null);
                },
                onError: (err) => toast.error(err.message),
              },
            );
          }}
          onCancel={() => {
            setShowRemoveConfirm(false);
            setIngredientToRemove(null);
          }}
          isLoading={removeIngredient.isPending}
        />
      )}

      {/* Delete confirmation */}
      {showDeleteConfirm && recipe && (
        <ConfirmModal
          title={`Supprimer « ${recipe.name} » ?`}
          message="Cette action est irréversible."
          onConfirm={handleDelete}
          onCancel={() => setShowDeleteConfirm(false)}
          isLoading={deleteMutation.isPending}
        />
      )}
    </div>
  );
}
