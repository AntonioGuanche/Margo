import { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  Link2,
  X,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { useInvoice, useConfirmInvoice, usePatchInvoice } from '../hooks/useInvoices';
import { useIngredients } from '../hooks/useIngredients';
import { useRecipes } from '../hooks/useRecipes';
import type { InvoiceLineResponse } from '../hooks/useInvoices';

type IngredientItem = { id: number; name: string };

interface LineState {
  description: string;
  quantity: number | null;
  unit: string | null;
  unit_price: number | null;
  total_price: number | null;
  units_per_package: number | null;
  ingredient_id: number | null;
  create_ingredient_name: string | null;
  ignored: boolean;
  match_confidence: string;
  suggestions: { id: number; name: string; score: number }[];
  is_manual: boolean;
  add_to_recipe_id: number | null;
  recipe_quantity: number | null;
  recipe_unit: string | null;
  create_recipe_name: string | null;
  create_recipe_price: number | null;
  create_recipe_category: string | null;
  create_recipe_is_homemade: boolean;
}

const UNIT_OPTIONS = ['g', 'kg', 'cl', 'l', 'pce'];
const RECIPE_CATEGORIES = ['entrée', 'plat', 'dessert', 'boisson', 'autre'];

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
  const [showRecipeLink, setShowRecipeLink] = useState(line.add_to_recipe_id != null);

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
      onChange({ ingredient_id: parseInt(value, 10), create_ingredient_name: null, ignored: false });
    }
  };

  const handleCreateName = (name: string) => {
    setNewName(name);
    onChange({ create_ingredient_name: name || null });
  };

  const matchedId = line.ingredient_id;
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

      {/* Ingredient match dropdown — only when not ignored */}
      {!line.ignored && (
        <div className="space-y-2">
          <select
            value={
              line.ignored
                ? '__ignore__'
                : line.create_ingredient_name
                  ? '__create__'
                  : line.ingredient_id?.toString() ?? ''
            }
            onChange={handleSelectIngredient}
            className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          >
            <option value="">Choisir un ingrédient...</option>

            {/* Suggestions from matching */}
            {line.suggestions.length > 0 && (
              <optgroup label="Suggestions">
                {line.suggestions.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({(s.score * 100).toFixed(0)}%)
                  </option>
                ))}
              </optgroup>
            )}

            {/* All ingredients not in suggestions */}
            <optgroup label="Tous les ingrédients">
              {allIngredients
                .filter((i) => !suggestionIds.has(i.id) && i.id !== matchedId)
                .map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.name}
                  </option>
                ))}
            </optgroup>

            <option value="__create__">+ Créer un nouvel ingrédient</option>
            <option value="__ignore__">Ignorer cette ligne</option>
          </select>

          {/* Create new ingredient input */}
          {showCreate && (
            <div className="flex gap-2">
              <input
                type="text"
                value={newName}
                onChange={(e) => handleCreateName(e.target.value)}
                placeholder="Nom du nouvel ingrédient"
                className="flex-1 border border-stone-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
              />
              <Plus size={18} className="text-emerald-600 self-center" />
            </div>
          )}

          {/* Add to recipe / create recipe */}
          {(line.ingredient_id || line.create_ingredient_name) && (
            <>
              {!showRecipeLink ? (
                <button
                  onClick={() => setShowRecipeLink(true)}
                  className="text-xs text-stone-500 hover:text-blue-600 flex items-center gap-1 mt-1"
                >
                  <Link2 size={12} />
                  Ajouter à une recette
                </button>
              ) : (
                <div className="mt-2 p-3 bg-blue-50 rounded-lg border border-blue-100 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-blue-700">
                      Ajouter à une recette
                    </span>
                    <button
                      onClick={() => {
                        setShowRecipeLink(false);
                        onChange({
                          add_to_recipe_id: null,
                          recipe_quantity: null,
                          recipe_unit: null,
                          create_recipe_name: null,
                          create_recipe_price: null,
                          create_recipe_category: null,
                          create_recipe_is_homemade: false,
                        });
                      }}
                      className="p-0.5 text-blue-400 hover:text-blue-600"
                    >
                      <X size={14} />
                    </button>
                  </div>

                  <select
                    value={
                      line.create_recipe_name != null
                        ? '__create__'
                        : line.add_to_recipe_id?.toString() ?? ''
                    }
                    onChange={(e) => {
                      if (e.target.value === '__create__') {
                        onChange({
                          add_to_recipe_id: null,
                          create_recipe_name: line.description,
                          create_recipe_price: null,
                          create_recipe_category: 'boisson',
                          create_recipe_is_homemade: false,
                        });
                      } else {
                        onChange({
                          add_to_recipe_id: e.target.value ? parseInt(e.target.value, 10) : null,
                          create_recipe_name: null,
                          create_recipe_price: null,
                          create_recipe_category: null,
                          create_recipe_is_homemade: false,
                        });
                      }
                    }}
                    className="w-full border border-blue-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Choisir une recette...</option>
                    <option value="__create__">+ Créer un nouveau produit</option>
                    {recipesList.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>

                  {/* Create new recipe form */}
                  {line.create_recipe_name != null && (
                    <div className="space-y-2 p-2 bg-white rounded-lg border border-blue-200">
                      <input
                        type="text"
                        value={line.create_recipe_name}
                        onChange={(e) => onChange({ create_recipe_name: e.target.value })}
                        placeholder="Nom du produit"
                        className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <div className="flex gap-2">
                        <input
                          type="number"
                          value={line.create_recipe_price ?? ''}
                          onChange={(e) =>
                            onChange({
                              create_recipe_price: e.target.value
                                ? parseFloat(e.target.value)
                                : null,
                            })
                          }
                          placeholder="Prix de vente (€)"
                          step="0.50"
                          className="flex-1 border border-stone-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <select
                          value={line.create_recipe_category ?? 'boisson'}
                          onChange={(e) => onChange({ create_recipe_category: e.target.value })}
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
                          checked={line.create_recipe_is_homemade}
                          onChange={(e) =>
                            onChange({ create_recipe_is_homemade: e.target.checked })
                          }
                          className="rounded border-stone-300 text-orange-600 focus:ring-orange-500"
                        />
                        Plat maison
                      </label>
                    </div>
                  )}

                  {/* Quantity & unit for recipe association */}
                  {(line.add_to_recipe_id || line.create_recipe_name) && (
                    <div className="flex gap-2">
                      <input
                        type="number"
                        value={line.recipe_quantity ?? ''}
                        onChange={(e) =>
                          onChange({
                            recipe_quantity: e.target.value ? parseFloat(e.target.value) : null,
                          })
                        }
                        placeholder="Quantité par portion"
                        step="0.1"
                        className="flex-1 border border-blue-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <select
                        value={line.recipe_unit ?? 'g'}
                        onChange={(e) => onChange({ recipe_unit: e.target.value })}
                        className="w-24 border border-blue-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        {UNIT_OPTIONS.map((u) => (
                          <option key={u} value={u}>
                            {u}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

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
        ingredient_id: l.matched_ingredient_id,
        create_ingredient_name: null,
        ignored: false,
        match_confidence: l.match_confidence,
        suggestions: l.suggestions,
        is_manual: false,
        add_to_recipe_id: null,
        recipe_quantity: null,
        recipe_unit: null,
        create_recipe_name: null,
        create_recipe_price: null,
        create_recipe_category: null,
        create_recipe_is_homemade: false,
      })),
    );
    setEditSupplier(invoice.supplier_name ?? '');
    setEditDate(invoice.invoice_date ?? '');
    setInitialized(true);
  }

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

  const allIngredients: IngredientItem[] = (ingredientsData?.items ?? []).map(
    (i: { id: number; name: string }) => ({ id: i.id, name: i.name }),
  );

  const recipesList = (recipesData?.items ?? []).map((r) => ({ id: r.id, name: r.name }));

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
        ingredient_id: null,
        create_ingredient_name: null,
        ignored: false,
        match_confidence: 'manual',
        suggestions: [],
        is_manual: true,
        add_to_recipe_id: null,
        recipe_quantity: null,
        recipe_unit: null,
        create_recipe_name: null,
        create_recipe_price: null,
        create_recipe_category: null,
        create_recipe_is_homemade: false,
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
        add_to_recipe_id: l.add_to_recipe_id ?? undefined,
        recipe_quantity: l.recipe_quantity ?? undefined,
        recipe_unit: l.recipe_unit ?? undefined,
        create_recipe_name: l.create_recipe_name ?? undefined,
        create_recipe_price: l.create_recipe_price ?? undefined,
        create_recipe_category: l.create_recipe_category ?? undefined,
        create_recipe_is_homemade: l.create_recipe_name ? l.create_recipe_is_homemade : undefined,
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
