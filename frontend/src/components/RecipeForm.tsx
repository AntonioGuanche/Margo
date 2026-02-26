import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Trash2 } from 'lucide-react';
import { useIngredients } from '../hooks/useIngredients';
import { useCreateRecipe, useUpdateRecipe, useRecipe } from '../hooks/useRecipes';
import type { Ingredient } from '../types';

interface IngredientLine {
  ingredient_id: number | null;
  quantity: string;
  unit: string;
  // For display
  ingredient_name?: string;
  unit_cost?: number | null;
}

const CATEGORIES = ['Entrée', 'Plat', 'Dessert', 'Boisson', 'Accompagnement', 'Autre'];

function calculateLineCost(quantity: string, unitCost: number | null | undefined): number | null {
  if (!quantity || unitCost == null) return null;
  const q = parseFloat(quantity);
  if (isNaN(q)) return null;
  return q * unitCost;
}

export default function RecipeForm({ recipeId }: { recipeId?: number }) {
  const navigate = useNavigate();
  const { data: ingredientsList } = useIngredients();
  const { data: existingRecipe } = useRecipe(recipeId ?? null);
  const createMutation = useCreateRecipe();
  const updateMutation = useUpdateRecipe();

  const [name, setName] = useState('');
  const [sellingPrice, setSellingPrice] = useState('');
  const [category, setCategory] = useState('');
  const [targetMargin, setTargetMargin] = useState('');
  const [isHomemade, setIsHomemade] = useState(true);
  const [linkedIngredientId, setLinkedIngredientId] = useState<number | null>(null);
  const [lines, setLines] = useState<IngredientLine[]>([
    { ingredient_id: null, quantity: '', unit: 'kg' },
  ]);

  // Populate form if editing
  useEffect(() => {
    if (existingRecipe) {
      setName(existingRecipe.name);
      setSellingPrice(existingRecipe.selling_price.toString());
      setCategory(existingRecipe.category ?? '');
      setTargetMargin(existingRecipe.target_margin?.toString() ?? '');
      setIsHomemade(existingRecipe.is_homemade);
      if (!existingRecipe.is_homemade && existingRecipe.ingredients.length > 0) {
        setLinkedIngredientId(existingRecipe.ingredients[0].ingredient_id);
      }
      setLines(
        existingRecipe.ingredients.map((ri) => ({
          ingredient_id: ri.ingredient_id,
          quantity: ri.quantity.toString(),
          unit: ri.unit,
          ingredient_name: ri.ingredient_name,
          unit_cost: ri.unit_cost,
        })),
      );
    }
  }, [existingRecipe]);

  const ingredientsMap = new Map<number, Ingredient>();
  if (ingredientsList) {
    for (const ing of ingredientsList.items) {
      ingredientsMap.set(ing.id, ing);
    }
  }

  // Live food cost calculation
  let totalCost = 0;
  if (isHomemade) {
    totalCost = lines.reduce((sum, line) => {
      if (!line.ingredient_id) return sum;
      const ing = ingredientsMap.get(line.ingredient_id);
      const lineCost = calculateLineCost(line.quantity, ing?.current_price ?? line.unit_cost);
      return sum + (lineCost ?? 0);
    }, 0);
  } else if (linkedIngredientId) {
    const linkedIng = ingredientsMap.get(linkedIngredientId);
    totalCost = linkedIng?.current_price ?? 0;
  }

  const sp = parseFloat(sellingPrice);
  const foodCostPercent = sp > 0 && totalCost > 0 ? (totalCost / sp) * 100 : null;

  function updateLine(index: number, updates: Partial<IngredientLine>) {
    setLines((prev) =>
      prev.map((line, i) => {
        if (i !== index) return line;
        const updated = { ...line, ...updates };
        // Auto-set unit when selecting ingredient
        if (updates.ingredient_id != null) {
          const ing = ingredientsMap.get(updates.ingredient_id);
          if (ing) {
            updated.unit = ing.unit;
            updated.unit_cost = ing.current_price;
          }
        }
        return updated;
      }),
    );
  }

  function addLine() {
    setLines((prev) => [...prev, { ingredient_id: null, quantity: '', unit: 'kg' }]);
  }

  function removeLine(index: number) {
    setLines((prev) => prev.filter((_, i) => i !== index));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    let ingredients: { ingredient_id: number; quantity: number; unit: string }[] = [];

    if (isHomemade) {
      const validLines = lines.filter(
        (l) => l.ingredient_id !== null && l.quantity && parseFloat(l.quantity) > 0,
      );
      if (validLines.length === 0) return;
      ingredients = validLines.map((l) => ({
        ingredient_id: l.ingredient_id!,
        quantity: parseFloat(l.quantity),
        unit: l.unit,
      }));
    } else if (linkedIngredientId) {
      // Bought product: link single ingredient with quantity=1
      const linkedIng = ingredientsMap.get(linkedIngredientId);
      ingredients = [{ ingredient_id: linkedIngredientId, quantity: 1, unit: linkedIng?.unit ?? 'piece' }];
    }

    const payload = {
      name: name.trim(),
      selling_price: parseFloat(sellingPrice),
      category: category || null,
      target_margin: targetMargin ? parseFloat(targetMargin) : null,
      is_homemade: isHomemade,
      ingredients,
    };

    if (recipeId) {
      updateMutation.mutate(
        { id: recipeId, data: payload },
        { onSuccess: () => navigate(`/recipes/${recipeId}`) },
      );
    } else {
      createMutation.mutate(payload, {
        onSuccess: (recipe) => navigate(`/recipes/${recipe.id}`),
      });
    }
  }

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <div>
      {/* Back */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-stone-500 hover:text-stone-700 text-sm mb-4"
      >
        <ArrowLeft size={16} />
        Retour
      </button>

      <h2 className="text-xl font-semibold text-stone-900 mb-4">
        {recipeId ? 'Modifier la recette' : 'Nouvelle recette'}
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">Nom</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border border-stone-300 rounded-lg px-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
            placeholder="Ex: Salade Caprese"
            required
            autoFocus
          />
        </div>

        {/* Selling price + category */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Prix de vente (€)</label>
            <input
              type="number"
              value={sellingPrice}
              onChange={(e) => setSellingPrice(e.target.value)}
              className="w-full border border-stone-300 rounded-lg px-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
              placeholder="14.50"
              step="0.01"
              min="0.01"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Catégorie</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full border border-stone-300 rounded-lg px-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
            >
              <option value="">—</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Target margin */}
        <div>
          <label className="block text-sm font-medium text-stone-700 mb-1">
            Marge cible (%) <span className="text-stone-400 font-normal">optionnel, défaut 30%</span>
          </label>
          <input
            type="number"
            value={targetMargin}
            onChange={(e) => setTargetMargin(e.target.value)}
            className="w-full border border-stone-300 rounded-lg px-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
            placeholder="30"
            step="1"
            min="0"
            max="100"
          />
        </div>

        {/* Homemade toggle */}
        <div className="flex items-center gap-3 bg-stone-50 rounded-lg p-3">
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={isHomemade}
              onChange={(e) => setIsHomemade(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-9 h-5 bg-stone-300 peer-focus:ring-2 peer-focus:ring-orange-300 rounded-full peer peer-checked:bg-orange-600 transition-colors after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-full" />
          </label>
          <div>
            <span className="text-sm font-medium text-stone-900">
              {isHomemade ? 'Plat maison' : 'Produit acheté'}
            </span>
            <p className="text-xs text-stone-500">
              {isHomemade
                ? 'Avec sous-ingrédients et quantités'
                : 'Marge directe : prix d’achat vs prix de vente'}
            </p>
          </div>
        </div>

        {/* Bought product: simple ingredient picker */}
        {!isHomemade && (
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">Ingrédient lié (produit acheté)</label>
            <select
              value={linkedIngredientId ?? ''}
              onChange={(e) => setLinkedIngredientId(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full border border-stone-300 rounded-lg px-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
            >
              <option value="">Choisir un ingrédient...</option>
              {ingredientsList?.items.map((ing) => (
                <option key={ing.id} value={ing.id}>
                  {ing.name}{ing.current_price != null ? ` — ${ing.current_price.toFixed(2)} €` : ''}
                </option>
              ))}
            </select>
            {linkedIngredientId && (() => {
              const linked = ingredientsMap.get(linkedIngredientId);
              return linked?.current_price != null ? (
                <p className="text-sm text-stone-500 mt-1">
                  Prix d’achat : <span className="font-semibold text-stone-900">{linked.current_price.toFixed(2)} €</span>
                </p>
              ) : (
                <p className="text-sm text-stone-400 mt-1">Pas encore de prix d’achat</p>
              );
            })()}
          </div>
        )}

        {/* Ingredients (homemade only) */}
        {isHomemade && <div>
          <label className="block text-sm font-medium text-stone-700 mb-2">Ingrédients</label>
          <div className="space-y-2">
            {lines.map((line, index) => {
              const ing = line.ingredient_id ? ingredientsMap.get(line.ingredient_id) : null;
              const unitCost = ing?.current_price ?? line.unit_cost ?? null;
              const lineCost = calculateLineCost(line.quantity, unitCost);

              return (
                <div key={index} className="bg-white border border-stone-200 rounded-lg p-3">
                  <div className="flex gap-2 items-start">
                    {/* Ingredient select */}
                    <select
                      value={line.ingredient_id ?? ''}
                      onChange={(e) =>
                        updateLine(index, {
                          ingredient_id: e.target.value ? parseInt(e.target.value) : null,
                        })
                      }
                      className="flex-1 border border-stone-300 rounded-lg px-3 py-2 text-sm text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
                    >
                      <option value="">Choisir un ingrédient</option>
                      {ingredientsList?.items.map((ing) => (
                        <option key={ing.id} value={ing.id}>
                          {ing.name} ({ing.unit}{ing.current_price != null ? ` — ${ing.current_price.toFixed(2)} €` : ''})
                        </option>
                      ))}
                    </select>

                    {/* Remove button */}
                    {lines.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeLine(index)}
                        className="p-2 text-stone-400 hover:text-red-600 transition-colors"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>

                  {/* Quantity + unit + line cost */}
                  <div className="flex gap-2 mt-2 items-center">
                    <input
                      type="number"
                      value={line.quantity}
                      onChange={(e) => updateLine(index, { quantity: e.target.value })}
                      className="w-24 border border-stone-300 rounded-lg px-3 py-2 text-sm text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
                      placeholder="Qté"
                      step="0.01"
                      min="0.01"
                    />
                    <span className="text-sm text-stone-500 w-12">{line.unit}</span>
                    {lineCost != null && (
                      <span className="text-sm font-medium text-emerald-600 ml-auto">
                        {lineCost.toFixed(2)} €
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <button
            type="button"
            onClick={addLine}
            className="mt-2 flex items-center gap-1 text-sm text-orange-700 hover:text-orange-800 font-medium"
          >
            <Plus size={16} />
            Ajouter un ingrédient
          </button>
        </div>}

        {/* Live food cost preview */}
        {totalCost > 0 && (
          <div className={`rounded-lg border p-3 ${
            foodCostPercent !== null && foodCostPercent > 35
              ? 'bg-red-50 border-red-200'
              : foodCostPercent !== null && foodCostPercent > 30
                ? 'bg-amber-50 border-amber-200'
                : 'bg-emerald-50 border-emerald-200'
          }`}>
            <div className="flex justify-between text-sm">
              <span className="text-stone-600">Coût total</span>
              <span className="font-semibold text-stone-900">{totalCost.toFixed(2)} €</span>
            </div>
            {foodCostPercent !== null && (
              <div className="flex justify-between text-sm mt-1">
                <span className="text-stone-600">Food cost</span>
                <span className={`font-semibold ${
                  foodCostPercent > 35
                    ? 'text-red-700'
                    : foodCostPercent > 30
                      ? 'text-amber-700'
                      : 'text-emerald-700'
                }`}>
                  {foodCostPercent.toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading || !name.trim() || !sellingPrice || (isHomemade && lines.every((l) => !l.ingredient_id))}
          className="w-full bg-orange-700 text-white py-2.5 rounded-lg font-medium hover:bg-orange-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? 'Enregistrement...' : recipeId ? 'Modifier' : 'Créer la recette'}
        </button>
      </form>
    </div>
  );
}
