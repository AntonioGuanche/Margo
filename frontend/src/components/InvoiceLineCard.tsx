import { useState } from 'react';
import {
  AlertTriangle,
  Check,
  Pencil,
  Trash2,
  Undo2,
  X,
} from 'lucide-react';
import ConfidenceBadge from './ConfidenceBadge';
import QuickRenameModal from './QuickRenameModal';
import PackagingEditor from './PackagingEditor';
import RecipeLinker from './RecipeLinker';
import type { LineState, IngredientItem } from '../types';

function cleanIngredientName(description: string, _volumeLiters: number | null): string {
  let name = description;
  // Remove volume patterns: "50 L", "50L", "0.75L", "20 L IFK"
  name = name.replace(/\d+([.,]\d+)?\s*[lL](\s|$)/g, ' ');
  // Remove packaging keywords
  name = name.replace(/\b(fût|fut|bag in box|bib|ifk|casier|caisse|cs|bac)\b/gi, ' ');
  // Clean up: trim, collapse spaces, title case
  name = name.replace(/\s+/g, ' ').trim();
  name = name
    .split(' ')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ');
  return name || description;
}

export default function InvoiceLineCard({
  line,
  allIngredients,
  recipesList,
  onChange,
  useAbsolutePrices,
  onRenameIngredient,
  onRenameRecipe,
}: {
  line: LineState;
  allIngredients: IngredientItem[];
  recipesList: { id: number; name: string }[];
  onChange: (updates: Partial<LineState>) => void;
  useAbsolutePrices?: boolean;
  onRenameIngredient?: (ingredientId: number, newName: string) => Promise<void>;
  onRenameRecipe?: (recipeId: number, newName: string) => Promise<void>;
}) {
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [renamingIngredient, setRenamingIngredient] = useState(false);
  const [isRenamingLoading, setIsRenamingLoading] = useState(false);
  const [localIngredientName, setLocalIngredientName] = useState<string | null>(null);

  const displayQty = useAbsolutePrices && line.quantity != null ? Math.abs(line.quantity) : line.quantity;
  const displayUnitPrice = useAbsolutePrices && line.unit_price != null ? Math.abs(line.unit_price) : line.unit_price;
  const displayTotal = useAbsolutePrices && line.total_price != null ? Math.abs(line.total_price) : line.total_price;

  const handleSelectIngredient = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    if (value === '__create__') {
      const cleaned = cleanIngredientName(line.description, line.volume_liters ?? null);
      setShowCreate(true);
      setNewName(cleaned);
      onChange({ ingredient_id: null, create_ingredient_name: cleaned, ignored: false });
    } else if (value === '__ignore__') {
      onChange({ ingredient_id: null, create_ingredient_name: null, ignored: true });
    } else {
      setShowCreate(false);
      setLocalIngredientName(null);
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
      <div className="flex items-start justify-between gap-2 flex-wrap sm:flex-nowrap mb-3">
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
              {displayQty != null && (
                <span>
                  {displayQty} {line.unit ?? ''}
                </span>
              )}
              {displayUnitPrice != null && <span>{displayUnitPrice.toFixed(2)} €/unité</span>}
              {displayTotal != null && <span>Total: {displayTotal.toFixed(2)} €</span>}
            </div>
          )}

          {/* Packaging editor — for all non-manual, non-ignored lines */}
          {!line.is_manual && !line.ignored && (
            <PackagingEditor
              detectedUnits={line.units_per_package}
              detectedClPerUnit={
                line.volume_liters && line.units_per_package
                  ? Math.round(line.volume_liters * 100 / line.units_per_package)
                  : null
              }
              detectedVolumeLiters={line.volume_liters}
              packagingUnits={line.packaging_units}
              packagingClPerUnit={line.packaging_cl_per_unit}
              totalPrice={line.total_price}
              quantity={line.quantity}
              onChange={(updates) => onChange({
                packaging_units: updates.packaging_units,
                packaging_cl_per_unit: updates.packaging_cl_per_unit,
                volume_liters: updates.volume_liters,
              })}
            />
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
          {/* No-match help banner */}
          {!line.ingredient_id && !line.create_ingredient_name && (
            <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 flex items-center gap-2">
              <AlertTriangle size={14} className="shrink-0" />
              <span>Choisis un ingrédient ci-dessous pour mettre à jour son prix.</span>
            </div>
          )}

          {line.ingredient_id || line.create_ingredient_name ? (
            /* CHIP MODE — ingrédient assigné */
            <>
              <div className="flex items-center gap-2">
                <div className="inline-flex items-center gap-2 bg-orange-50 border border-orange-200 rounded-lg px-3 py-1.5 text-sm">
                  <span className="text-orange-800 font-medium">
                    {line.create_ingredient_name
                      ? line.create_ingredient_name
                      : localIngredientName ?? allIngredients.find(i => i.id === line.ingredient_id)?.name ?? 'Ingrédient'}
                  </span>
                  {!line.create_ingredient_name && line.ingredient_id && onRenameIngredient && (
                    <button
                      onClick={() => setRenamingIngredient(true)}
                      className="text-stone-400 hover:text-orange-600 transition-colors"
                      title="Renommer l'ingrédient"
                    >
                      <Pencil size={12} />
                    </button>
                  )}
                  {line.volume_liters && (
                    <span className="text-blue-500 text-xs">— en €/l</span>
                  )}
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
                      setLocalIngredientName(null);
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
                  <option value="__create__">+ Créer un nouvel ingrédient</option>
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
              <option value="__create__">+ Créer un nouvel ingrédient</option>
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
              volumeInfo={
                line.volume_liters && line.suggested_serving_cl
                  ? { servingCl: line.suggested_serving_cl }
                  : undefined
              }
              onChange={(links) => onChange({ recipe_links: links })}
              onRenameRecipe={onRenameRecipe}
            />
          )}
        </div>
      )}

      {/* Quick rename modal for existing ingredient */}
      {renamingIngredient && line.ingredient_id && (
        <QuickRenameModal
          title="Renommer l'ingrédient"
          currentName={localIngredientName ?? allIngredients.find(i => i.id === line.ingredient_id)?.name ?? ''}
          isLoading={isRenamingLoading}
          onCancel={() => setRenamingIngredient(false)}
          onSave={async (newIngName) => {
            if (!onRenameIngredient) return;
            setIsRenamingLoading(true);
            try {
              await onRenameIngredient(line.ingredient_id!, newIngName);
              setLocalIngredientName(newIngName);
              setRenamingIngredient(false);
            } finally {
              setIsRenamingLoading(false);
            }
          }}
        />
      )}
    </div>
  );
}
