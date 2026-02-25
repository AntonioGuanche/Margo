import { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowLeft,
  FileCheck,
  Check,
  Plus,
  Loader2,
  Pencil,
  Trash2,
  Undo2,
  X,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { useInvoice, useConfirmInvoice, usePatchInvoice } from '../hooks/useInvoices';
import { useIngredients } from '../hooks/useIngredients';
import { useRecipes } from '../hooks/useRecipes';
import { apiClient } from '../api/client';
import type { InvoiceLineResponse } from '../hooks/useInvoices';

type IngredientItem = { id: number; name: string };

// --- Recipe link types ---

type RecipeLinkState = {
  recipe_id: number | null;
  recipe_name: string;
  quantity: number;
  unit: string;
  is_new: boolean;
  // For creation
  create_recipe_name?: string;
  create_recipe_price?: number;
  create_recipe_category?: string;
  create_recipe_is_homemade?: boolean;
};

interface IngredientRecipeItem {
  recipe_id: number;
  recipe_name: string;
  category: string | null;
  quantity: number;
  unit: string;
}

// --- Line state ---

interface LineState {
  description: string;
  quantity: number | null;
  unit: string | null;
  unit_price: number | null;
  total_price: number | null;
  units_per_package: number | null;
  volume_liters: number | null;
  serving_type: string | null;
  suggested_serving_cl: number | null;
  suggested_portions: number | null;
  price_per_portion: number | null;
  ingredient_id: number | null;
  create_ingredient_name: string | null;
  ignored: boolean;
  match_confidence: string;
  suggestions: { id: number; name: string; score: number }[];
  is_manual: boolean;
  recipe_links: RecipeLinkState[];
}

const RECIPE_CATEGORIES = ['entrée', 'plat', 'dessert', 'boisson', 'autre'];

// --- Confidence badge ---

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const styles = {
    exact: 'bg-emerald-50 text-emerald-700',
    alias: 'bg-emerald-50 text-emerald-700',
    fuzzy: 'bg-amber-50 text-amber-700',
    none: 'bg-red-50 text-red-700',
    manual: 'bg-blue-50 text-blue-700',
  } as const;
  const labels = {
    exact: 'Exact',
    alias: 'Alias',
    fuzzy: 'Fuzzy',
    none: 'Aucun match',
    manual: 'Manuel',
  } as const;
  const style = styles[confidence as keyof typeof styles] ?? styles.none;
  const label = labels[confidence as keyof typeof labels] ?? 'Inconnu';

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style}`}>
      {label}
    </span>
  );
}

// --- RecipeLinker: chip-based multi-recipe with auto-suggestion ---

function RecipeLinker({
  ingredientId,
  recipeLinks,
  recipesList,
  lineDescription,
  onChange,
}: {
  ingredientId: number | null;
  recipeLinks: RecipeLinkState[];
  recipesList: { id: number; name: string }[];
  lineDescription: string;
  onChange: (links: RecipeLinkState[]) => void;
}) {
  const [showAdd, setShowAdd] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newRecipeName, setNewRecipeName] = useState('');
  const [newRecipePrice, setNewRecipePrice] = useState<number | null>(null);
  const [newRecipeCategory, setNewRecipeCategory] = useState('boisson');
  const [newRecipeIsHomemade, setNewRecipeIsHomemade] = useState(false);
  const [autoSuggested, setAutoSuggested] = useState(false);

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
  useEffect(() => {
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
  }, [existingRecipes, autoSuggested]); // eslint-disable-line react-hooks/exhaustive-deps

  function addRecipe(recipeId: number) {
    const recipe = recipesList.find((r) => r.id === recipeId);
    if (!recipe || recipeLinks.some((l) => l.recipe_id === recipeId)) return;
    onChange([
      ...recipeLinks,
      {
        recipe_id: recipeId,
        recipe_name: recipe.name,
        quantity: 1,
        unit: 'piece',
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
        quantity: 1,
        unit: 'piece',
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
            {recipesList
              .filter((r) => !recipeLinks.some((l) => l.recipe_id === r.id))
              .map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            <option value="__create__">+ Créer un nouveau produit</option>
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
              {RECIPE_CATEGORIES.map((c) => (
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

// --- LineRow ---

function LineRow({
  line,
  allIngredients,
  recipesList,
  onChange,
}: {
  line: LineState;
  allIngredients: IngredientItem[];
  recipesList: { id: number; name: string }[];
  onChange: (updates: Partial<LineState>) => void;
}) {
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const handleSelectIngredient = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    if (value === '__create__') {
      setShowCreate(true);
      setNewName(line.description);
      onChange({ ingredient_id: null, create_ingredient_name: line.description, ignored: false });
    } else if (value === '__ignore__') {
      onChange({ ingredient_id: null, create_ingredient_name: null, ignored: true });
    } else {
      setShowCreate(false);
      onChange({ ingredient_id: parseInt(value, 10), create_ingredient_name: null, ignored: false, recipe_links: [] });
    }
  };

  const handleCreateName = (name: string) => {
    setNewName(name);
    onChange({ create_ingredient_name: name || null });
  };

  const suggestionIds = new Set(line.suggestions.map((s) => s.id));

  return (
    <div
      className={`bg-white rounded-xl border ${
        line.is_manual ? 'border-blue-200' : 'border-stone-200'
      } p-4 ${line.ignored ? 'opacity-50' : ''}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex-1 min-w-0">
          {line.is_manual ? (
            <input
              type="text"
              value={line.description}
              onChange={(e) => onChange({ description: e.target.value })}
              placeholder="Nom du produit"
              className="font-medium text-stone-900 w-full bg-transparent border-b border-blue-200 focus:border-blue-500 focus:outline-none py-0.5"
            />
          ) : (
            <p className="font-medium text-stone-900 truncate">{line.description}</p>
          )}

          {line.is_manual ? (
            <div className="flex gap-2 mt-1.5">
              <input
                type="number"
                value={line.quantity ?? ''}
                onChange={(e) =>
                  onChange({ quantity: e.target.value ? parseFloat(e.target.value) : null })
                }
                placeholder="Qté"
                step="0.1"
                className="w-20 border border-stone-300 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="text"
                value={line.unit ?? ''}
                onChange={(e) => onChange({ unit: e.target.value || null })}
                placeholder="kg, L, pce..."
                className="w-24 border border-stone-300 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="number"
                value={line.unit_price ?? ''}
                onChange={(e) =>
                  onChange({ unit_price: e.target.value ? parseFloat(e.target.value) : null })
                }
                placeholder="Prix unit."
                step="0.01"
                className="w-24 border border-stone-300 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <span className="self-center text-sm text-stone-400">€</span>
            </div>
          ) : (
            <div className="flex gap-3 text-sm text-stone-500 mt-0.5">
              {line.quantity != null && (
                <span>
                  {line.quantity} {line.unit ?? ''}
                </span>
              )}
              {line.unit_price != null && <span>{line.unit_price.toFixed(2)} €/unité</span>}
              {line.total_price != null && <span>Total: {line.total_price.toFixed(2)} €</span>}
            </div>
          )}

          {/* Conversion conditionnement → unités */}
          {!line.is_manual &&
            line.units_per_package != null &&
            line.units_per_package > 0 &&
            line.quantity != null &&
            line.quantity > 0 && (
              <div className="text-xs text-amber-700 bg-amber-50 rounded-lg px-2 py-1 mt-1 flex items-center gap-1">
                <span>💡</span>
                <span>
                  {line.quantity} {line.unit ?? 'colis'} × {line.units_per_package} ={' '}
                  {Math.round(line.quantity * line.units_per_package)} unités
                  {line.total_price != null && (
                    <>
                      {' '}
                      → {(line.total_price / (line.quantity * line.units_per_package)).toFixed(2)} €/unité
                    </>
                  )}
                </span>
              </div>
            )}

          {/* Portion calculation from volume (kegs, BIB, bottles) */}
          {!line.is_manual &&
            line.volume_liters != null &&
            line.suggested_portions != null &&
            line.suggested_portions > 0 && (
              <div className="text-xs bg-blue-50 rounded-lg px-2 py-1.5 mt-1 space-y-1">
                <div className="flex items-center gap-1 text-blue-700">
                  <span>🍺</span>
                  <span>
                    {line.volume_liters}L ÷ {line.suggested_serving_cl}cl
                    = <strong>{line.suggested_portions} portions</strong>
                    {line.price_per_portion != null && (
                      <> → <strong>{line.price_per_portion.toFixed(2)} €/portion</strong></>
                    )}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-blue-600">
                  <span className="text-[10px]">Taille service :</span>
                  <select
                    value={line.suggested_serving_cl ?? 25}
                    onChange={(e) => {
                      const newCl = parseFloat(e.target.value);
                      const newPortions = Math.floor((line.volume_liters! * 100) / newCl);
                      const newPrice = line.total_price && newPortions > 0
                        ? line.total_price / newPortions
                        : null;
                      onChange({
                        suggested_serving_cl: newCl,
                        suggested_portions: newPortions,
                        price_per_portion: newPrice,
                      });
                    }}
                    className="text-xs border border-blue-200 rounded px-1.5 py-0.5 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
                  >
                    <option value="25">25cl (bière)</option>
                    <option value="33">33cl (bière)</option>
                    <option value="50">50cl (pinte)</option>
                    <option value="12.5">12.5cl (vin)</option>
                    <option value="15">15cl (vin)</option>
                    <option value="4">4cl (alcool)</option>
                    <option value="2">2cl (shot)</option>
                  </select>
                </div>
              </div>
            )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <ConfidenceBadge confidence={line.match_confidence} />
          {!line.ignored ? (
            <button
              onClick={() =>
                onChange({ ignored: true, ingredient_id: null, create_ingredient_name: null })
              }
              className="p-1 text-stone-400 hover:text-red-600 transition-colors"
              title="Ignorer cette ligne"
            >
              <Trash2 size={14} />
            </button>
          ) : (
            <button
              onClick={() => onChange({ ignored: false })}
              className="p-1 text-stone-400 hover:text-orange-600 transition-colors"
              title="Restaurer cette ligne"
            >
              <Undo2 size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Ingredient assignment — only when not ignored */}
      {!line.ignored && (
        <div className="space-y-2">
          {line.ingredient_id || line.create_ingredient_name ? (
            /* CHIP MODE — ingrédient assigné */
            <>
              <div className="flex items-center gap-2">
                <div className="inline-flex items-center gap-2 bg-orange-50 border border-orange-200 rounded-lg px-3 py-1.5 text-sm">
                  <span className="text-orange-800 font-medium">
                    {line.create_ingredient_name
                      ? line.create_ingredient_name
                      : allIngredients.find(i => i.id === line.ingredient_id)?.name ?? 'Ingrédient'}
                  </span>
                  {line.create_ingredient_name && (
                    <span className="text-emerald-600 text-xs flex items-center gap-0.5">
                      <Check size={12} />
                      Sera créé
                    </span>
                  )}
                  {!line.create_ingredient_name && line.ingredient_id && (() => {
                    const suggestion = line.suggestions.find(s => s.id === line.ingredient_id);
                    return suggestion ? (
                      <span className="text-orange-500 text-xs">
                        ({(suggestion.score * 100).toFixed(0)}%)
                      </span>
                    ) : null;
                  })()}
                  <button
                    onClick={() => {
                      setShowCreate(false);
                      onChange({ ingredient_id: null, create_ingredient_name: null, recipe_links: [] });
                    }}
                    className="text-stone-400 hover:text-red-500 transition-colors ml-1"
                    title="Retirer l'association"
                  >
                    <X size={14} />
                  </button>
                </div>
                <button
                  onClick={() => setShowDropdown(true)}
                  className="text-xs text-stone-400 hover:text-orange-600"
                >
                  Changer
                </button>
              </div>

              {/* Dropdown override quand on clique "Changer" */}
              {showDropdown && (
                <select
                  value=""
                  onChange={(e) => {
                    handleSelectIngredient(e);
                    setShowDropdown(false);
                  }}
                  onBlur={() => setShowDropdown(false)}
                  autoFocus
                  className="w-full border border-orange-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                >
                  <option value="">Choisir un autre ingrédient...</option>
                  {line.suggestions.length > 0 && (
                    <optgroup label="Suggestions">
                      {line.suggestions.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name} ({(s.score * 100).toFixed(0)}%)
                        </option>
                      ))}
                    </optgroup>
                  )}
                  <optgroup label="Tous les ingrédients">
                    {allIngredients
                      .filter((i) => !suggestionIds.has(i.id))
                      .map((i) => (
                        <option key={i.id} value={i.id}>
                          {i.name}
                        </option>
                      ))}
                  </optgroup>
                  <option value="__create__">+ Créer un nouvel ingrédient</option>
                </select>
              )}
            </>
          ) : (
            /* DROPDOWN MODE — pas d'ingrédient assigné */
            <select
              value=""
              onChange={handleSelectIngredient}
              className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            >
              <option value="">Choisir un ingrédient...</option>
              {line.suggestions.length > 0 && (
                <optgroup label="Suggestions">
                  {line.suggestions.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({(s.score * 100).toFixed(0)}%)
                    </option>
                  ))}
                </optgroup>
              )}
              <optgroup label="Tous les ingrédients">
                {allIngredients
                  .filter((i) => !suggestionIds.has(i.id))
                  .map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.name}
                    </option>
                  ))}
              </optgroup>
              <option value="__create__">+ Créer un nouvel ingrédient</option>
              <option value="__ignore__">Ignorer cette ligne</option>
            </select>
          )}

          {/* Create new ingredient input */}
          {showCreate && (
            <div>
              <div className="flex gap-2 items-center">
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => handleCreateName(e.target.value)}
                  placeholder="Nom du nouvel ingrédient"
                  className="flex-1 border border-stone-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                />
                {newName.trim() ? (
                  <span className="flex items-center gap-1 text-emerald-600 text-xs font-medium whitespace-nowrap">
                    <Check size={14} />
                    Sera créé
                  </span>
                ) : (
                  <span className="text-xs text-stone-400 whitespace-nowrap">Entrez un nom</span>
                )}
              </div>
              {newName.trim() && (
                <p className="text-xs text-stone-400 mt-0.5">
                  L'ingrédient sera créé automatiquement à la confirmation de la facture.
                </p>
              )}
            </div>
          )}

          {/* RecipeLinker — multi-recipe chip system with auto-suggestion */}
          {(line.ingredient_id || line.create_ingredient_name) && (
            <RecipeLinker
              ingredientId={line.ingredient_id}
              recipeLinks={line.recipe_links}
              recipesList={recipesList}
              lineDescription={line.description}
              onChange={(links) => onChange({ recipe_links: links })}
            />
          )}
        </div>
      )}
    </div>
  );
}

// --- Main page ---

export default function InvoiceReview() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: invoice, isLoading } = useInvoice(id);
  const { data: ingredientsData } = useIngredients();
  const { data: recipesData } = useRecipes();
  const confirm = useConfirmInvoice(id ?? '0');
  const patchInvoice = usePatchInvoice(id ?? '0');
  const [showResult, setShowResult] = useState(false);

  const [lines, setLines] = useState<LineState[]>([]);
  const [initialized, setInitialized] = useState(false);
  const [recipesPreFilled, setRecipesPreFilled] = useState(false);
  const [editSupplier, setEditSupplier] = useState('');
  const [editDate, setEditDate] = useState('');
  const [showIgnored, setShowIgnored] = useState(true);

  // Initialize line state from fetched data
  if (invoice && !initialized) {
    setLines(
      invoice.lines.map((l: InvoiceLineResponse) => ({
        description: l.description,
        quantity: l.quantity,
        unit: l.unit,
        unit_price: l.unit_price,
        total_price: l.total_price,
        units_per_package: l.units_per_package,
        volume_liters: l.volume_liters,
        serving_type: l.serving_type,
        suggested_serving_cl: l.suggested_serving_cl,
        suggested_portions: l.suggested_portions,
        price_per_portion: l.price_per_portion,
        ingredient_id: l.matched_ingredient_id,
        create_ingredient_name: null,
        ignored: false,
        match_confidence: l.match_confidence,
        suggestions: l.suggestions,
        is_manual: false,
        recipe_links: [],
      })),
    );
    setEditSupplier(invoice.supplier_name ?? '');
    setEditDate(invoice.invoice_date ?? '');
    setInitialized(true);
  }

  const allIngredients: IngredientItem[] = (ingredientsData?.items ?? []).map(
    (i: { id: number; name: string }) => ({ id: i.id, name: i.name }),
  );

  const recipesList = (recipesData?.items ?? []).map((r) => ({ id: r.id, name: r.name }));

  // Batch-fetch recipes for all matched ingredients after init
  useEffect(() => {
    if (!initialized || recipesPreFilled || lines.length === 0) return;

    const ingredientIds = [
      ...new Set(
        lines
          .filter((l) => l.ingredient_id && l.recipe_links.length === 0)
          .map((l) => l.ingredient_id!),
      ),
    ];

    if (ingredientIds.length === 0) {
      setRecipesPreFilled(true);
      return;
    }

    apiClient<{ results: Record<number, IngredientRecipeItem[]> }>(
      '/api/ingredients/recipes-batch',
      { method: 'POST', body: { ingredient_ids: ingredientIds } },
    )
      .then((data) => {
        setLines((prev) =>
          prev.map((line) => {
            if (!line.ingredient_id || line.recipe_links.length > 0) return line;
            const recipes = data.results[line.ingredient_id] || [];
            if (recipes.length > 0) {
              return {
                ...line,
                recipe_links: recipes.map((r) => ({
                  recipe_id: r.recipe_id,
                  recipe_name: r.recipe_name,
                  quantity: r.quantity,
                  unit: r.unit,
                  is_new: false,
                })),
              };
            }

            // Fallback: match by name similarity
            const ingName =
              allIngredients
                .find((i) => i.id === line.ingredient_id)
                ?.name?.toLowerCase() ?? '';
            if (!ingName) return line;

            const stopWords = new Set([
              'de', 'le', 'la', 'les', 'du', 'des', 'un', 'une',
              'biere', 'bière', 'vin', 'eau',
            ]);
            const ingWords = ingName
              .split(/[\s-]+/)
              .filter((w) => w.length > 2 && !stopWords.has(w));
            if (ingWords.length === 0) return line;

            const matches = recipesList.filter((r) => {
              const rWords = r.name.toLowerCase().split(/[\s-]+/);
              return ingWords.some((w) =>
                rWords.some((rw) => rw.includes(w) || w.includes(rw)),
              );
            });

            if (matches.length > 0 && matches.length <= 5) {
              return {
                ...line,
                recipe_links: matches.map((r) => ({
                  recipe_id: r.id,
                  recipe_name: r.name,
                  quantity: 1,
                  unit: 'piece',
                  is_new: false,
                })),
              };
            }
            return line;
          }),
        );
        setRecipesPreFilled(true);
      })
      .catch(() => {
        setRecipesPreFilled(true);
      });
  }, [initialized, recipesPreFilled, lines.length]); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePatchField = (field: 'supplier_name' | 'invoice_date', value: string) => {
    if (!value.trim()) return;
    const current = field === 'supplier_name' ? invoice?.supplier_name : invoice?.invoice_date;
    if (value === (current ?? '')) return;
    patchInvoice.mutate(
      { [field]: value },
      {
        onSuccess: () =>
          toast.success(
            field === 'supplier_name' ? 'Fournisseur mis à jour' : 'Date mise à jour',
          ),
        onError: (err) => toast.error(err.message),
      },
    );
  };

  const updateLine = (index: number, updates: Partial<LineState>) => {
    setLines((prev) => prev.map((l, i) => (i === index ? { ...l, ...updates } : l)));
  };

  const addManualLine = useCallback(() => {
    setLines((prev) => [
      ...prev,
      {
        description: '',
        quantity: null,
        unit: null,
        unit_price: null,
        total_price: null,
        units_per_package: null,
        volume_liters: null,
        serving_type: null,
        suggested_serving_cl: null,
        suggested_portions: null,
        price_per_portion: null,
        ingredient_id: null,
        create_ingredient_name: null,
        ignored: false,
        match_confidence: 'manual',
        suggestions: [],
        is_manual: true,
        recipe_links: [],
      },
    ]);
  }, []);

  // Split lines into active and ignored (keeping original indices)
  const activeLines = lines
    .map((line, index) => ({ line, index }))
    .filter((item) => !item.line.ignored);
  const ignoredLines = lines
    .map((line, index) => ({ line, index }))
    .filter((item) => item.line.ignored);

  const handleConfirm = () => {
    const confirmLines = lines
      .filter((l) => !l.ignored)
      .map((l) => ({
        description: l.description,
        ingredient_id: l.ingredient_id,
        create_ingredient_name: l.create_ingredient_name,
        unit_price: l.unit_price,
        unit: l.unit,
        recipe_links: l.recipe_links
          .filter((rl) => rl.recipe_id || rl.create_recipe_name)
          .map((rl) => ({
            recipe_id: rl.recipe_id ?? undefined,
            create_recipe_name: rl.create_recipe_name ?? undefined,
            create_recipe_price: rl.create_recipe_price ?? undefined,
            create_recipe_category: rl.create_recipe_category ?? undefined,
            create_recipe_is_homemade: rl.create_recipe_name ? rl.create_recipe_is_homemade : undefined,
            quantity: rl.quantity,
            unit: rl.unit,
          })),
      }));

    confirm.mutate(confirmLines, {
      onSuccess: (data) => {
        setShowResult(true);
        toast.success(`Facture confirmée — ${data.prices_updated} prix mis à jour ✅`);
      },
      onError: (err) => toast.error(err.message),
    });
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-700" />
      </div>
    );
  }

  if (!invoice) {
    return <p className="text-center text-stone-500 py-12">Facture introuvable</p>;
  }

  // Success screen
  if (showResult && confirm.data) {
    return (
      <div className="text-center py-12">
        <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Check size={32} className="text-emerald-600" />
        </div>
        <h2 className="text-xl font-semibold text-stone-900 mb-4">Facture confirmée !</h2>
        <div className="bg-white rounded-xl border border-stone-200 p-6 text-left space-y-2 mb-6 max-w-sm mx-auto">
          <p className="text-sm text-stone-600">
            <span className="font-semibold text-stone-900">{confirm.data.prices_updated}</span> prix
            mis à jour
          </p>
          <p className="text-sm text-stone-600">
            <span className="font-semibold text-stone-900">
              {confirm.data.ingredients_created}
            </span>{' '}
            ingrédient{confirm.data.ingredients_created > 1 ? 's' : ''} créé
            {confirm.data.ingredients_created > 1 ? 's' : ''}
          </p>
          <p className="text-sm text-stone-600">
            <span className="font-semibold text-stone-900">{confirm.data.aliases_saved}</span> alias
            mémorisé{confirm.data.aliases_saved > 1 ? 's' : ''}
          </p>
          <p className="text-sm text-stone-600">
            <span className="font-semibold text-stone-900">
              {confirm.data.recipes_recalculated}
            </span>{' '}
            recette{confirm.data.recipes_recalculated > 1 ? 's' : ''} recalculée
            {confirm.data.recipes_recalculated > 1 ? 's' : ''}
          </p>
          {confirm.data.recipes_created > 0 && (
            <p className="text-sm text-stone-600">
              <span className="font-semibold text-stone-900">
                {confirm.data.recipes_created}
              </span>{' '}
              produit{confirm.data.recipes_created > 1 ? 's' : ''} créé
              {confirm.data.recipes_created > 1 ? 's' : ''}
            </p>
          )}
        </div>
        <button
          onClick={() => navigate('/invoices')}
          className="bg-orange-700 text-white px-6 py-3 rounded-xl font-medium hover:bg-orange-800 transition-colors"
        >
          Voir mes factures
        </button>
      </div>
    );
  }

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
      <h2 className="text-xl font-semibold text-stone-900 mb-1 flex items-center gap-2">
        <FileCheck size={22} className="text-orange-700" />
        Vérifier la facture
      </h2>

      {/* Invoice metadata — editable supplier & date */}
      <div className="bg-white rounded-xl border border-stone-200 p-4 mb-4">
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-stone-500 flex items-center gap-1">
              Fournisseur <Pencil size={12} className="text-stone-400" />
            </span>
            <input
              type="text"
              value={editSupplier}
              onChange={(e) => setEditSupplier(e.target.value)}
              onBlur={() => handlePatchField('supplier_name', editSupplier)}
              placeholder="Nom du fournisseur"
              className="w-full font-medium text-stone-900 bg-transparent border-b border-transparent hover:border-stone-300 focus:border-orange-500 focus:outline-none py-0.5 transition-colors"
            />
          </div>
          <div>
            <span className="text-stone-500 flex items-center gap-1">
              Date <Pencil size={12} className="text-stone-400" />
            </span>
            <input
              type="date"
              value={editDate}
              onChange={(e) => {
                setEditDate(e.target.value);
                handlePatchField('invoice_date', e.target.value);
              }}
              className="w-full font-medium text-stone-900 bg-transparent border-b border-transparent hover:border-stone-300 focus:border-orange-500 focus:outline-none py-0.5 transition-colors"
            />
          </div>
          {invoice.total_amount != null && (
            <div>
              <span className="text-stone-500">Montant total</span>
              <p className="font-medium text-stone-900">{invoice.total_amount.toFixed(2)} €</p>
            </div>
          )}
          <div>
            <span className="text-stone-500">Format</span>
            <p className="font-medium text-stone-900 uppercase">{invoice.format}</p>
          </div>
        </div>
      </div>

      {/* Lines header */}
      <h3 className="text-sm font-medium text-stone-500 uppercase tracking-wide mb-2">
        {activeLines.length} ligne{activeLines.length > 1 ? 's' : ''} active
        {activeLines.length > 1 ? 's' : ''}
      </h3>

      {/* Active lines */}
      <div className="space-y-3 mb-4">
        {activeLines.map(({ line, index }) => (
          <LineRow
            key={index}
            line={line}
            allIngredients={allIngredients}
            recipesList={recipesList}
            onChange={(updates) => updateLine(index, updates)}
          />
        ))}
      </div>

      {/* Add manual line button */}
      <button
        onClick={addManualLine}
        className="w-full border-2 border-dashed border-stone-300 rounded-xl py-3 text-sm font-medium text-stone-500 hover:border-blue-400 hover:text-blue-600 transition-colors flex items-center justify-center gap-2 mb-4"
      >
        <Plus size={16} />
        Ajouter une ligne
      </button>

      {/* Ignored lines group */}
      {ignoredLines.length > 0 && (
        <div className="mb-6">
          <button
            onClick={() => setShowIgnored((prev) => !prev)}
            className="flex items-center gap-1 text-sm text-stone-400 hover:text-stone-600 mb-2"
          >
            {showIgnored ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            Lignes ignorées ({ignoredLines.length})
          </button>
          {showIgnored && (
            <div className="space-y-2">
              {ignoredLines.map(({ line, index }) => (
                <LineRow
                  key={index}
                  line={line}
                  allIngredients={allIngredients}
                  recipesList={recipesList}
                  onChange={(updates) => updateLine(index, updates)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {lines.length === 0 && invoice.raw_text && (
        <div className="bg-stone-50 rounded-xl border border-stone-200 p-4 mb-6">
          <p className="text-sm text-stone-500 mb-2">
            Extraction automatique impossible. Texte brut extrait :
          </p>
          <pre className="text-xs text-stone-700 whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">
            {invoice.raw_text}
          </pre>
        </div>
      )}

      {/* Confirm button */}
      <button
        onClick={handleConfirm}
        disabled={confirm.isPending}
        className="w-full bg-orange-700 text-white py-3 rounded-xl font-medium hover:bg-orange-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
      >
        {confirm.isPending ? (
          <>
            <Loader2 size={18} className="animate-spin" />
            Confirmation...
          </>
        ) : (
          <>
            <Check size={18} />
            Confirmer tout
          </>
        )}
      </button>

      {/* Error */}
      {confirm.isError && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {confirm.error.message}
        </div>
      )}
    </div>
  );
}
