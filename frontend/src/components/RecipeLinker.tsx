import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Check, Pencil, Plus, X } from 'lucide-react';
import { apiClient } from '../api/client';
import type { RecipeLinkState, IngredientRecipeItem } from '../types';
import QuickRenameModal from './QuickRenameModal';

const CATEGORIES = ['entrée', 'plat', 'dessert', 'boisson', 'autre'];

interface VolumeInfo {
  servingCl: number;
}

export default function RecipeLinker({
  ingredientId,
  recipeLinks,
  recipesList,
  lineDescription,
  volumeInfo,
  skipAutoSuggest,
  onChange,
  onRenameRecipe,
}: {
  ingredientId: number | null;
  recipeLinks: RecipeLinkState[];
  recipesList: { id: number; name: string }[];
  lineDescription: string;
  volumeInfo?: VolumeInfo;
  skipAutoSuggest?: boolean;
  onChange: (links: RecipeLinkState[]) => void;
  onRenameRecipe?: (recipeId: number, newName: string) => Promise<void>;
}) {
  const [showAdd, setShowAdd] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newRecipeName, setNewRecipeName] = useState('');
  const [newRecipePrice, setNewRecipePrice] = useState<number | null>(null);
  const [newRecipeCategory, setNewRecipeCategory] = useState('boisson');
  const [newRecipeIsHomemade, setNewRecipeIsHomemade] = useState(false);
  const [autoSuggested, setAutoSuggested] = useState(false);
  const [renamingIdx, setRenamingIdx] = useState<number | null>(null);
  const [isRenamingRecipe, setIsRenamingRecipe] = useState(false);

  // Reset auto-suggestion flag when ingredient changes
  useEffect(() => {
    setAutoSuggested(false);
  }, [ingredientId]);

  // Auto-fetch recipes that already use this ingredient
  const { data: existingRecipes } = useQuery<{ items: IngredientRecipeItem[] }>({
    queryKey: ['ingredient-recipes', ingredientId],
    queryFn: () =>
      apiClient<{ items: IngredientRecipeItem[] }>(
        `/api/ingredients/${ingredientId}/recipes`,
      ),
    enabled: !!ingredientId,
  });

  // Auto-suggest when ingredient has existing recipes and links are empty
  // SKIP if draft recipe links exist (user has already made deliberate choices)
  useEffect(() => {
    if (skipAutoSuggest) return;
    if (existingRecipes?.items && existingRecipes.items.length > 0 && recipeLinks.length === 0 && !autoSuggested) {
      setAutoSuggested(true);
      onChange(
        existingRecipes.items.map((r) => ({
          recipe_id: r.recipe_id,
          recipe_name: r.recipe_name,
          quantity: r.quantity,
          unit: r.unit,
          is_new: false,
        })),
      );
    }
  }, [existingRecipes, autoSuggested, skipAutoSuggest]); // eslint-disable-line react-hooks/exhaustive-deps

  function addRecipe(recipeId: number) {
    const recipe = recipesList.find((r) => r.id === recipeId);
    if (!recipe || recipeLinks.some((l) => l.recipe_id === recipeId)) return;
    onChange([
      ...recipeLinks,
      {
        recipe_id: recipeId,
        recipe_name: recipe.name,
        quantity: volumeInfo?.servingCl ?? 1,
        unit: volumeInfo ? 'cl' : 'piece',
        is_new: false,
      },
    ]);
    setShowAdd(false);
  }

  function addNewRecipe() {
    if (!newRecipeName.trim()) return;
    onChange([
      ...recipeLinks,
      {
        recipe_id: null,
        recipe_name: newRecipeName,
        quantity: volumeInfo?.servingCl ?? 1,
        unit: volumeInfo ? 'cl' : 'piece',
        is_new: true,
        create_recipe_name: newRecipeName,
        create_recipe_price: newRecipePrice ?? undefined,
        create_recipe_category: newRecipeCategory,
        create_recipe_is_homemade: newRecipeIsHomemade,
      },
    ]);
    setShowCreateForm(false);
    setShowAdd(false);
    setNewRecipeName('');
    setNewRecipePrice(null);
    setNewRecipeCategory('boisson');
    setNewRecipeIsHomemade(false);
  }

  function removeRecipe(index: number) {
    onChange(recipeLinks.filter((_, i) => i !== index));
  }

  function updateRecipe(index: number, updates: Partial<RecipeLinkState>) {
    onChange(recipeLinks.map((l, i) => (i === index ? { ...l, ...updates } : l)));
  }

  return (
    <div className="mt-2 space-y-1.5">
      {/* Existing recipe chips */}
      {recipeLinks.map((link, idx) => (
        <div
          key={idx}
          className="flex items-center gap-2 bg-blue-50 border border-blue-100 rounded-lg px-3 py-1.5"
        >
          <span className="text-sm font-medium text-blue-800 flex-1 truncate">
            {link.recipe_name}
          </span>
          {!link.is_new && onRenameRecipe && (
            <button
              onClick={() => setRenamingIdx(idx)}
              className="text-stone-400 hover:text-blue-600 transition-colors shrink-0"
              title="Renommer la recette"
            >
              <Pencil size={12} />
            </button>
          )}
          {link.is_new && (
            <span className="text-emerald-600 text-xs flex items-center gap-0.5 shrink-0">
              <Check size={12} />
              Nouveau
            </span>
          )}
          <input
            type="number"
            value={link.quantity}
            onChange={(e) =>
              updateRecipe(idx, { quantity: parseFloat(e.target.value) || 0 })
            }
            className="w-16 border border-blue-200 rounded px-1.5 py-0.5 text-xs text-center bg-white"
            step="0.01"
            placeholder="Qté"
          />
          <select
            value={link.unit}
            onChange={(e) => updateRecipe(idx, { unit: e.target.value })}
            className="border border-blue-200 rounded px-1 py-0.5 text-xs bg-white"
          >
            <option value="g">g</option>
            <option value="kg">kg</option>
            <option value="cl">cl</option>
            <option value="l">l</option>
            <option value="piece">pce</option>
          </select>
          <button
            onClick={() => removeRecipe(idx)}
            className="text-blue-300 hover:text-red-500 transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      ))}

      {/* Rename recipe modal */}
      {renamingIdx !== null && recipeLinks[renamingIdx] && (
        <QuickRenameModal
          title="Renommer la recette"
          currentName={recipeLinks[renamingIdx].recipe_name}
          isLoading={isRenamingRecipe}
          onCancel={() => setRenamingIdx(null)}
          onSave={async (newName) => {
            const link = recipeLinks[renamingIdx];
            if (!onRenameRecipe || !link.recipe_id) return;
            setIsRenamingRecipe(true);
            try {
              await onRenameRecipe(link.recipe_id, newName);
              onChange(recipeLinks.map((l, i) => i === renamingIdx ? { ...l, recipe_name: newName } : l));
              setRenamingIdx(null);
            } finally {
              setIsRenamingRecipe(false);
            }
          }}
        />
      )}

      {/* Add recipe button/dropdown */}
      {!showAdd ? (
        <button
          onClick={() => setShowAdd(true)}
          className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
        >
          <Plus size={12} />
          Ajouter à une recette
        </button>
      ) : !showCreateForm ? (
        <div className="space-y-2">
          <select
            value=""
            onChange={(e) => {
              if (e.target.value === '__create__') {
                setShowCreateForm(true);
                setNewRecipeName(lineDescription);
              } else if (e.target.value) {
                addRecipe(parseInt(e.target.value));
              }
            }}
            onBlur={() => {
              // Delay to allow click on create option
              setTimeout(() => {
                if (!showCreateForm) setShowAdd(false);
              }, 200);
            }}
            autoFocus
            className="w-full border border-blue-300 rounded-lg px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            <option value="">Choisir une recette...</option>
            <option value="__create__">+ Créer un nouveau produit</option>
            {recipesList
              .filter((r) => !recipeLinks.some((l) => l.recipe_id === r.id))
              .map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
          </select>
        </div>
      ) : (
        /* Create new recipe form */
        <div className="space-y-2 p-3 bg-blue-50 rounded-lg border border-blue-100">
          <input
            type="text"
            value={newRecipeName}
            onChange={(e) => setNewRecipeName(e.target.value)}
            placeholder="Nom du produit"
            className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <div className="flex gap-2">
            <input
              type="number"
              value={newRecipePrice ?? ''}
              onChange={(e) =>
                setNewRecipePrice(e.target.value ? parseFloat(e.target.value) : null)
              }
              placeholder="Prix de vente (€)"
              step="0.50"
              className="flex-1 border border-stone-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <select
              value={newRecipeCategory}
              onChange={(e) => setNewRecipeCategory(e.target.value)}
              className="w-28 border border-stone-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c.charAt(0).toUpperCase() + c.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-stone-600">
            <input
              type="checkbox"
              checked={newRecipeIsHomemade}
              onChange={(e) => setNewRecipeIsHomemade(e.target.checked)}
              className="rounded border-stone-300 text-orange-600 focus:ring-orange-500"
            />
            Plat maison
          </label>
          <div className="flex gap-2">
            <button
              onClick={addNewRecipe}
              disabled={!newRecipeName.trim()}
              className="flex-1 bg-blue-600 text-white rounded-lg px-3 py-1.5 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              Créer
            </button>
            <button
              onClick={() => {
                setShowCreateForm(false);
                setShowAdd(false);
              }}
              className="px-3 py-1.5 text-sm text-stone-500 hover:text-stone-700"
            >
              Annuler
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
