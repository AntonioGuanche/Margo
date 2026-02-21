import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, SlidersHorizontal, Check } from 'lucide-react';
import { useRecipe } from '../hooks/useRecipes';
import { useSimulate, useApplySimulation } from '../hooks/useSimulator';
import type { SimulateResponse } from '../hooks/useSimulator';

const STATUS_COLORS = {
  green: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500', border: 'border-emerald-200', label: 'OK' },
  orange: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500', border: 'border-amber-200', label: 'Attention' },
  red: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500', border: 'border-red-200', label: 'Critique' },
} as const;

function getMarginStatus(foodCostPercent: number, target = 30): 'green' | 'orange' | 'red' {
  if (foodCostPercent < target) return 'green';
  if (foodCostPercent <= target + 5) return 'orange';
  return 'red';
}

function StatusDot({ status }: { status: 'green' | 'orange' | 'red' }) {
  const c = STATUS_COLORS[status];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}

export default function Simulator() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const recipeId = id ? parseInt(id) : 0;
  const { data: recipe, isLoading: recipeLoading } = useRecipe(recipeId || null);
  const simulate = useSimulate(recipeId);
  const apply = useApplySimulation(recipeId);

  // Simulation state (loaded once from API)
  const [baseData, setBaseData] = useState<SimulateResponse | null>(null);

  // User-controlled values
  const [sellingPrice, setSellingPrice] = useState<number>(0);
  const [quantities, setQuantities] = useState<Record<number, number>>({});
  const [weeklySales, setWeeklySales] = useState<number | ''>('');
  const [applied, setApplied] = useState(false);

  // Fetch initial simulation data
  useEffect(() => {
    if (recipeId && !baseData) {
      simulate.mutate({}, {
        onSuccess: (data) => {
          setBaseData(data);
          setSellingPrice(data.current.selling_price);
          const qtys: Record<number, number> = {};
          for (const ing of data.current.ingredients) {
            qtys[ing.ingredient_id] = ing.quantity;
          }
          setQuantities(qtys);
        },
      });
    }
  }, [recipeId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Client-side simulation (no API call on slider movement)
  const simulated = useMemo(() => {
    if (!baseData) return null;

    let foodCost = 0;
    const ingredients = baseData.current.ingredients.map((ing) => {
      const qty = quantities[ing.ingredient_id] ?? ing.quantity;
      const unitPrice = ing.unit_price ?? 0;
      const lineCost = qty * unitPrice;
      foodCost += lineCost;

      return {
        ...ing,
        quantity: qty,
        line_cost: Math.round(lineCost * 10000) / 10000,
        changed: qty !== ing.quantity,
      };
    });

    const sp = sellingPrice;
    const fcp = sp > 0 ? Math.round((foodCost / sp) * 10000) / 100 : 0;
    const grossMargin = Math.round((sp - foodCost) * 100) / 100;
    const status = getMarginStatus(fcp);

    let monthlyImpact: number | null = null;
    if (weeklySales !== '' && weeklySales > 0) {
      const currentMargin = baseData.current.gross_margin;
      monthlyImpact = Math.round((grossMargin - currentMargin) * weeklySales * 4 * 100) / 100;
    }

    return {
      selling_price: sp,
      food_cost: Math.round(foodCost * 100) / 100,
      food_cost_percent: fcp,
      margin_status: status,
      gross_margin: grossMargin,
      ingredients,
      monthly_impact: monthlyImpact,
    };
  }, [baseData, sellingPrice, quantities, weeklySales]);

  function handleApply() {
    const adjustments = baseData?.current.ingredients
      .filter((ing) => (quantities[ing.ingredient_id] ?? ing.quantity) !== ing.quantity)
      .map((ing) => ({
        ingredient_id: ing.ingredient_id,
        new_quantity: quantities[ing.ingredient_id],
      })) ?? [];

    apply.mutate(
      {
        new_selling_price: sellingPrice !== baseData?.current.selling_price ? sellingPrice : undefined,
        ingredient_adjustments: adjustments.length > 0 ? adjustments : undefined,
      },
      {
        onSuccess: () => {
          setApplied(true);
          setTimeout(() => navigate(`/recipes/${recipeId}`), 1500);
        },
      },
    );
  }

  if (recipeLoading || simulate.isPending) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-700" />
      </div>
    );
  }

  if (!recipe || !baseData || !simulated) {
    return (
      <div className="text-center py-12">
        <p className="text-stone-500">Recette introuvable</p>
        <button onClick={() => navigate(-1)} className="text-orange-700 hover:underline text-sm mt-2">
          Retour
        </button>
      </div>
    );
  }

  if (applied) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mb-4">
          <Check size={32} className="text-emerald-600" />
        </div>
        <p className="text-lg font-semibold text-stone-900">Modifications appliquées !</p>
        <p className="text-sm text-stone-500 mt-1">Redirection...</p>
      </div>
    );
  }

  const current = baseData.current;
  const currentStatus = current.margin_status as 'green' | 'orange' | 'red';
  const simStatus = simulated.margin_status;

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

      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <SlidersHorizontal size={22} className="text-orange-700" />
        <div>
          <h2 className="text-xl font-bold text-stone-900">{baseData.recipe_name}</h2>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-sm text-stone-500">Food cost actuel :</span>
            <span className={`text-sm font-semibold ${STATUS_COLORS[currentStatus].text}`}>
              {current.food_cost_percent.toFixed(1)}%
            </span>
            <StatusDot status={currentStatus} />
          </div>
        </div>
      </div>

      {/* Selling price slider */}
      <div className="bg-white rounded-xl border border-stone-200 p-4 mb-3">
        <label className="text-sm font-medium text-stone-700 block mb-2">Prix de vente</label>
        <p className="text-3xl font-bold text-stone-900 text-center mb-2">
          {sellingPrice.toFixed(2)} €
        </p>
        <input
          type="range"
          min={1}
          max={Math.round(current.selling_price * 3)}
          step={0.5}
          value={sellingPrice}
          onChange={(e) => setSellingPrice(parseFloat(e.target.value))}
          className="w-full accent-orange-700"
        />
        <div className="flex justify-between text-xs text-stone-400 mt-1">
          <span>1 €</span>
          <span>{Math.round(current.selling_price * 3)} €</span>
        </div>
      </div>

      {/* Ingredient portion sliders */}
      <div className="bg-white rounded-xl border border-stone-200 p-4 mb-3">
        <label className="text-sm font-medium text-stone-700 block mb-3">Portions ingrédients</label>
        <div className="space-y-4">
          {current.ingredients.map((ing) => {
            const currentQty = quantities[ing.ingredient_id] ?? ing.quantity;
            const pct = ing.quantity > 0 ? Math.round((currentQty / ing.quantity) * 100) : 100;

            return (
              <div key={ing.ingredient_id}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-stone-900">{ing.ingredient_name}</span>
                  <span className={`text-xs font-medium ${pct !== 100 ? 'text-orange-700' : 'text-stone-400'}`}>
                    {currentQty.toFixed(2)} {ing.unit} ({pct}%)
                  </span>
                </div>
                <input
                  type="range"
                  min={Math.round(ing.quantity * 50) / 100}
                  max={Math.round(ing.quantity * 150) / 100}
                  step={Math.round(ing.quantity * 5) / 100 || 0.01}
                  value={currentQty}
                  onChange={(e) =>
                    setQuantities((prev) => ({
                      ...prev,
                      [ing.ingredient_id]: parseFloat(e.target.value),
                    }))
                  }
                  className="w-full accent-orange-700"
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* Weekly sales input */}
      <div className="bg-white rounded-xl border border-stone-200 p-4 mb-4">
        <label className="text-sm font-medium text-stone-700 block mb-2">
          Combien de fois par semaine ?
        </label>
        <input
          type="number"
          min={0}
          value={weeklySales}
          onChange={(e) => setWeeklySales(e.target.value ? parseInt(e.target.value) : '')}
          placeholder="ex: 30"
          className="w-full border border-stone-300 rounded-lg px-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
        />
      </div>

      {/* Result comparison */}
      <div className="bg-white rounded-xl border border-stone-200 overflow-hidden mb-4">
        <div className="grid grid-cols-2">
          <div className="p-3 text-center border-b border-r border-stone-200 bg-stone-50">
            <span className="text-xs font-medium text-stone-500 uppercase">Actuel</span>
          </div>
          <div className="p-3 text-center border-b border-stone-200 bg-orange-50">
            <span className="text-xs font-medium text-orange-700 uppercase">Simulé</span>
          </div>

          {/* Food cost */}
          <div className="p-3 border-b border-r border-stone-100 text-center">
            <p className="text-xs text-stone-500">Food cost</p>
            <p className="text-lg font-semibold text-stone-900">{current.food_cost.toFixed(2)} €</p>
          </div>
          <div className="p-3 border-b border-stone-100 text-center">
            <p className="text-xs text-stone-500">Food cost</p>
            <p className="text-lg font-semibold text-stone-900">{simulated.food_cost.toFixed(2)} €</p>
          </div>

          {/* Food cost % */}
          <div className="p-3 border-b border-r border-stone-100 text-center">
            <p className="text-xs text-stone-500">Food cost %</p>
            <p className={`text-lg font-semibold ${STATUS_COLORS[currentStatus].text}`}>
              {current.food_cost_percent.toFixed(1)}%
            </p>
          </div>
          <div className="p-3 border-b border-stone-100 text-center">
            <p className="text-xs text-stone-500">Food cost %</p>
            <p className={`text-lg font-semibold ${STATUS_COLORS[simStatus].text}`}>
              {simulated.food_cost_percent.toFixed(1)}%
            </p>
          </div>

          {/* Gross margin */}
          <div className="p-3 border-b border-r border-stone-100 text-center">
            <p className="text-xs text-stone-500">Marge brute</p>
            <p className="text-lg font-semibold text-stone-900">{current.gross_margin.toFixed(2)} €</p>
          </div>
          <div className="p-3 border-b border-stone-100 text-center">
            <p className="text-xs text-stone-500">Marge brute</p>
            <p className="text-lg font-semibold text-stone-900">{simulated.gross_margin.toFixed(2)} €</p>
          </div>

          {/* Status */}
          <div className="p-3 border-r border-stone-100 text-center">
            <p className="text-xs text-stone-500 mb-1">Status</p>
            <StatusDot status={currentStatus} />
          </div>
          <div className="p-3 text-center">
            <p className="text-xs text-stone-500 mb-1">Status</p>
            <StatusDot status={simStatus} />
          </div>
        </div>
      </div>

      {/* Monthly impact */}
      {simulated.monthly_impact !== null && (
        <div className={`rounded-xl border p-4 mb-4 text-center ${
          simulated.monthly_impact >= 0
            ? 'bg-emerald-50 border-emerald-200'
            : 'bg-red-50 border-red-200'
        }`}>
          <p className="text-sm text-stone-500">Impact mensuel</p>
          <p className={`text-2xl font-bold ${
            simulated.monthly_impact >= 0 ? 'text-emerald-700' : 'text-red-700'
          }`}>
            {simulated.monthly_impact >= 0 ? '+' : ''}{simulated.monthly_impact.toFixed(2)} €/mois
          </p>
          {simulated.monthly_impact > 0 && (
            <p className="text-xs text-emerald-600 mt-1">récupérés</p>
          )}
        </div>
      )}

      {/* Apply button */}
      <button
        onClick={handleApply}
        disabled={apply.isPending}
        className="w-full bg-orange-700 text-white px-4 py-3 rounded-xl font-medium hover:bg-orange-800 transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
      >
        {apply.isPending ? (
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
        ) : (
          <>
            <Check size={20} />
            Appliquer ces modifications
          </>
        )}
      </button>
    </div>
  );
}
