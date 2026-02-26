import { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  ArrowLeft,
  FileCheck,
  Check,
  Plus,
  Loader2,
  Pencil,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { useInvoice, useConfirmInvoice, usePatchInvoice } from '../hooks/useInvoices';
import { useIngredients } from '../hooks/useIngredients';
import { useRecipes } from '../hooks/useRecipes';
import { apiClient } from '../api/client';
import InvoiceLineCard from '../components/InvoiceLineCard';
import type { InvoiceLineResponse } from '../hooks/useInvoices';
import type { LineState, IngredientItem, IngredientRecipeItem } from '../types/invoice';

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
        <div className="flex flex-col gap-3 w-full max-w-xs mx-auto">
          <button
            onClick={() => navigate('/invoices/upload')}
            className="bg-orange-700 text-white px-6 py-3 rounded-xl font-medium hover:bg-orange-800 transition-colors flex items-center justify-center gap-2"
          >
            <Plus size={18} />
            Importer une autre facture
          </button>
          <button
            onClick={() => navigate('/invoices')}
            className="bg-stone-100 text-stone-700 px-6 py-3 rounded-xl font-medium hover:bg-stone-200 transition-colors"
          >
            Voir mes factures
          </button>
        </div>
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
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
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
          <InvoiceLineCard
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
                <InvoiceLineCard
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

      {/* Pre-confirm summary */}
      {(() => {
        const assignedCount = activeLines.filter(
          ({ line }) => line.ingredient_id || line.create_ingredient_name
        ).length;
        const newIngCount = activeLines.filter(
          ({ line }) => line.create_ingredient_name
        ).length;
        return (
          <>
            {assignedCount > 0 && (
              <div className="bg-stone-50 border border-stone-200 rounded-xl px-4 py-3 mb-3 text-sm text-stone-600 space-y-1">
                <p>
                  <span className="font-semibold text-stone-900">{assignedCount}</span> ligne{assignedCount > 1 ? 's' : ''}
                  {assignedCount > 1 ? ' seront traitées' : ' sera traitée'}
                </p>
                {newIngCount > 0 && (
                  <p>
                    <span className="font-semibold text-stone-900">{newIngCount}</span> nouvel ingrédient{newIngCount > 1 ? 's' : ''}
                    {newIngCount > 1 ? ' seront créés' : ' sera créé'}
                  </p>
                )}
                {ignoredLines.length > 0 && (
                  <p className="text-stone-400">
                    {ignoredLines.length} ligne{ignoredLines.length > 1 ? 's' : ''} ignorée{ignoredLines.length > 1 ? 's' : ''}
                  </p>
                )}
              </div>
            )}

            {assignedCount === 0 && activeLines.length > 0 && (
              <p className="text-sm text-amber-600 text-center mb-2">
                Assigne au moins un ingrédient pour confirmer la facture.
              </p>
            )}
          </>
        );
      })()}

      {/* Confirm button */}
      <button
        onClick={handleConfirm}
        disabled={confirm.isPending || activeLines.filter(({ line }) => line.ingredient_id || line.create_ingredient_name).length === 0}
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
