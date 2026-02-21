import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, Upload, Plus, Trash2, Check, ChevronDown, ChevronUp } from 'lucide-react';
import {
  useExtractMenu,
  useSuggestIngredients,
  useConfirmOnboarding,
} from '../hooks/useOnboarding';
import type { ExtractedDish, DishWithSuggestions } from '../hooks/useOnboarding';

const CATEGORIES = ['entrée', 'plat', 'dessert', 'boisson', 'autre'];
const UNITS = ['g', 'kg', 'cl', 'l', 'piece'];

function Stepper({ currentStep }: { currentStep: number }) {
  const steps = ['Photo', 'Plats', 'Ingrédients', 'Terminé'];
  return (
    <div className="flex items-center justify-center mb-6">
      {steps.map((label, i) => (
        <div key={i} className="flex items-center">
          <div className="flex flex-col items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
                i < currentStep
                  ? 'bg-orange-700 text-white'
                  : i === currentStep
                    ? 'bg-orange-700 text-white ring-4 ring-orange-200'
                    : 'bg-stone-200 text-stone-500'
              }`}
            >
              {i < currentStep ? <Check size={16} /> : i + 1}
            </div>
            <span className="text-xs mt-1 text-stone-500">{label}</span>
          </div>
          {i < steps.length - 1 && (
            <div
              className={`w-8 h-0.5 mx-1 mb-4 ${
                i < currentStep ? 'bg-orange-700' : 'bg-stone-200'
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ----- Step 1: Photo -----
function StepPhoto({
  onExtracted,
}: {
  onExtracted: (dishes: ExtractedDish[], imageSrc: string) => void;
}) {
  const [preview, setPreview] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const extractMutation = useExtractMenu();

  function handleFile(f: File) {
    setFile(f);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target?.result as string);
    reader.readAsDataURL(f);
  }

  function handleExtract() {
    if (!file) return;
    extractMutation.mutate(file, {
      onSuccess: (data) => onExtracted(data.dishes, preview!),
    });
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-stone-900 text-center">
        Photographiez votre carte
      </h3>
      <p className="text-sm text-stone-500 text-center">
        L'IA va extraire tous les plats avec leurs prix
      </p>

      {preview ? (
        <div className="relative">
          <img src={preview} alt="Menu" className="w-full rounded-xl border border-stone-200" />
          <button
            onClick={() => { setPreview(null); setFile(null); }}
            className="absolute top-2 right-2 bg-white/90 rounded-full p-1.5 text-stone-600 hover:text-red-600"
          >
            <Trash2 size={16} />
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <button
            onClick={() => cameraInputRef.current?.click()}
            className="w-full bg-orange-700 text-white py-4 rounded-xl font-medium hover:bg-orange-800 transition-colors flex items-center justify-center gap-2 text-lg"
          >
            <Camera size={24} />
            Photographier ma carte
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-full bg-white text-stone-700 py-3 rounded-xl font-medium border border-stone-300 hover:border-stone-400 transition-colors flex items-center justify-center gap-2"
          >
            <Upload size={18} />
            Choisir un fichier
          </button>
        </div>
      )}

      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />

      {file && (
        <button
          onClick={handleExtract}
          disabled={extractMutation.isPending}
          className="w-full bg-orange-700 text-white py-3 rounded-xl font-medium hover:bg-orange-800 disabled:opacity-50 transition-colors"
        >
          {extractMutation.isPending ? 'Extraction en cours...' : 'Extraire les plats →'}
        </button>
      )}

      {extractMutation.isError && (
        <p className="text-red-600 text-sm text-center">
          {extractMutation.error.message}
        </p>
      )}
    </div>
  );
}

// ----- Step 2: Review dishes -----
function StepDishes({
  dishes,
  onConfirm,
  isLoading,
}: {
  dishes: ExtractedDish[];
  onConfirm: (dishes: ExtractedDish[]) => void;
  isLoading: boolean;
}) {
  const [editableDishes, setEditableDishes] = useState(
    dishes.map((d) => ({ ...d, selected: true })),
  );

  function updateDish(index: number, updates: Partial<ExtractedDish & { selected: boolean }>) {
    setEditableDishes((prev) =>
      prev.map((d, i) => (i === index ? { ...d, ...updates } : d)),
    );
  }

  function addDish() {
    setEditableDishes((prev) => [
      ...prev,
      { name: '', price: null, category: 'plat', selected: true },
    ]);
  }

  function handleConfirm() {
    const selected = editableDishes
      .filter((d) => d.selected && d.name.trim())
      .map(({ name, price, category }) => ({ name: name.trim(), price, category }));
    onConfirm(selected);
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-stone-900">
        {editableDishes.length} plats extraits
      </h3>
      <p className="text-sm text-stone-500">
        Vérifiez et ajustez les plats. Décochez ceux à exclure.
      </p>

      <div className="space-y-2">
        {editableDishes.map((dish, index) => (
          <div
            key={index}
            className={`bg-white border rounded-xl p-3 transition-opacity ${
              dish.selected ? 'border-stone-200' : 'border-stone-100 opacity-50'
            }`}
          >
            <div className="flex items-center gap-2 mb-2">
              <input
                type="checkbox"
                checked={dish.selected}
                onChange={(e) => updateDish(index, { selected: e.target.checked })}
                className="w-4 h-4 accent-orange-700"
              />
              <input
                type="text"
                value={dish.name}
                onChange={(e) => updateDish(index, { name: e.target.value })}
                className="flex-1 border border-stone-300 rounded-lg px-2 py-1.5 text-sm text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
                placeholder="Nom du plat"
              />
            </div>
            <div className="flex gap-2 ml-6">
              <input
                type="number"
                value={dish.price ?? ''}
                onChange={(e) =>
                  updateDish(index, { price: e.target.value ? parseFloat(e.target.value) : null })
                }
                className="w-24 border border-stone-300 rounded-lg px-2 py-1.5 text-sm text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
                placeholder="Prix €"
                step="0.50"
                inputMode="decimal"
              />
              <select
                value={dish.category ?? 'plat'}
                onChange={(e) => updateDish(index, { category: e.target.value })}
                className="flex-1 border border-stone-300 rounded-lg px-2 py-1.5 text-sm text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={addDish}
        className="flex items-center gap-1 text-sm text-orange-700 hover:text-orange-800 font-medium"
      >
        <Plus size={16} />
        Ajouter un plat manuellement
      </button>

      <button
        onClick={handleConfirm}
        disabled={isLoading || editableDishes.every((d) => !d.selected)}
        className="w-full bg-orange-700 text-white py-3 rounded-xl font-medium hover:bg-orange-800 disabled:opacity-50 transition-colors"
      >
        {isLoading ? 'Suggestion des ingrédients...' : 'Proposer les ingrédients →'}
      </button>
    </div>
  );
}

// ----- Step 3: Review ingredients -----
function StepIngredients({
  dishes,
  onConfirm,
  isLoading,
}: {
  dishes: DishWithSuggestions[];
  onConfirm: (dishes: DishWithSuggestions[]) => void;
  isLoading: boolean;
}) {
  const [editableDishes, setEditableDishes] = useState(dishes);
  const [openIndex, setOpenIndex] = useState<number>(0);

  function updateIngredient(
    dishIdx: number,
    ingIdx: number,
    updates: Partial<{ name: string; quantity: number; unit: string }>,
  ) {
    setEditableDishes((prev) =>
      prev.map((d, di) =>
        di !== dishIdx
          ? d
          : {
              ...d,
              ingredients: d.ingredients.map((ing, ii) =>
                ii !== ingIdx ? ing : { ...ing, ...updates },
              ),
            },
      ),
    );
  }

  function removeIngredient(dishIdx: number, ingIdx: number) {
    setEditableDishes((prev) =>
      prev.map((d, di) =>
        di !== dishIdx
          ? d
          : { ...d, ingredients: d.ingredients.filter((_, ii) => ii !== ingIdx) },
      ),
    );
  }

  function addIngredient(dishIdx: number) {
    setEditableDishes((prev) =>
      prev.map((d, di) =>
        di !== dishIdx
          ? d
          : {
              ...d,
              ingredients: [...d.ingredients, { name: '', quantity: 0, unit: 'g' }],
            },
      ),
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-stone-900">
        Ingrédients suggérés
      </h3>
      <p className="text-sm text-stone-500">
        Ajustez les ingrédients et quantités pour chaque plat.
      </p>

      <div className="space-y-2">
        {editableDishes.map((dish, dishIdx) => (
          <div key={dishIdx} className="bg-white border border-stone-200 rounded-xl overflow-hidden">
            {/* Accordion header */}
            <button
              onClick={() => setOpenIndex(openIndex === dishIdx ? -1 : dishIdx)}
              className="w-full px-4 py-3 flex items-center justify-between text-left"
            >
              <div>
                <span className="font-medium text-stone-900">{dish.name}</span>
                <span className="text-sm text-stone-500 ml-2">
                  {dish.ingredients.length} ingrédient{dish.ingredients.length > 1 ? 's' : ''}
                </span>
              </div>
              {openIndex === dishIdx ? (
                <ChevronUp size={18} className="text-stone-400" />
              ) : (
                <ChevronDown size={18} className="text-stone-400" />
              )}
            </button>

            {/* Accordion body */}
            {openIndex === dishIdx && (
              <div className="px-4 pb-3 space-y-2 border-t border-stone-100 pt-3">
                {dish.ingredients.map((ing, ingIdx) => (
                  <div key={ingIdx} className="flex gap-2 items-center">
                    <input
                      type="text"
                      value={ing.name}
                      onChange={(e) =>
                        updateIngredient(dishIdx, ingIdx, { name: e.target.value })
                      }
                      className="flex-1 border border-stone-300 rounded-lg px-2 py-1.5 text-sm text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
                      placeholder="Ingrédient"
                    />
                    <input
                      type="number"
                      value={ing.quantity || ''}
                      onChange={(e) =>
                        updateIngredient(dishIdx, ingIdx, {
                          quantity: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-20 border border-stone-300 rounded-lg px-2 py-1.5 text-sm text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
                      placeholder="Qté"
                      inputMode="decimal"
                      step="0.1"
                    />
                    <select
                      value={ing.unit}
                      onChange={(e) =>
                        updateIngredient(dishIdx, ingIdx, { unit: e.target.value })
                      }
                      className="w-16 border border-stone-300 rounded-lg px-1 py-1.5 text-sm text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
                    >
                      {UNITS.map((u) => (
                        <option key={u} value={u}>{u}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => removeIngredient(dishIdx, ingIdx)}
                      className="p-1 text-stone-400 hover:text-red-600 transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
                <button
                  onClick={() => addIngredient(dishIdx)}
                  className="flex items-center gap-1 text-xs text-orange-700 hover:text-orange-800 font-medium mt-1"
                >
                  <Plus size={14} />
                  Ajouter un ingrédient
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      <button
        onClick={() => onConfirm(editableDishes)}
        disabled={isLoading}
        className="w-full bg-orange-700 text-white py-3 rounded-xl font-medium hover:bg-orange-800 disabled:opacity-50 transition-colors"
      >
        {isLoading ? 'Création en cours...' : 'Confirmer et créer →'}
      </button>
    </div>
  );
}

// ----- Step 4: Confirmation -----
function StepDone({
  recipesCreated,
  ingredientsCreated,
}: {
  recipesCreated: number;
  ingredientsCreated: number;
}) {
  const navigate = useNavigate();

  return (
    <div className="text-center space-y-4 py-8">
      <div className="text-6xl">🎉</div>
      <h3 className="text-xl font-bold text-stone-900">C'est fait !</h3>
      <p className="text-stone-600">
        <span className="font-semibold text-orange-700">{recipesCreated} recette{recipesCreated > 1 ? 's' : ''}</span>
        {' '}et{' '}
        <span className="font-semibold text-orange-700">{ingredientsCreated} ingrédient{ingredientsCreated > 1 ? 's' : ''}</span>
        {' '}créés
      </p>
      <p className="text-sm text-stone-500">
        Importez vos factures pour voir apparaître les prix et le food cost.
      </p>
      <button
        onClick={() => navigate('/')}
        className="bg-orange-700 text-white px-6 py-3 rounded-xl font-medium hover:bg-orange-800 transition-colors"
      >
        Voir mon dashboard →
      </button>
    </div>
  );
}

// ----- Main Onboarding page -----
export default function Onboarding() {
  const [step, setStep] = useState(0);
  const [extractedDishes, setExtractedDishes] = useState<ExtractedDish[]>([]);
  const [dishesWithIngredients, setDishesWithIngredients] = useState<DishWithSuggestions[]>([]);
  const [result, setResult] = useState<{ recipes: number; ingredients: number } | null>(null);

  const suggestMutation = useSuggestIngredients();
  const confirmMutation = useConfirmOnboarding();

  function handleExtracted(dishes: ExtractedDish[]) {
    setExtractedDishes(dishes);
    setStep(1);
  }

  function handleDishesConfirmed(dishes: ExtractedDish[]) {
    suggestMutation.mutate(dishes, {
      onSuccess: (data) => {
        setDishesWithIngredients(data.dishes);
        setStep(2);
      },
    });
  }

  function handleIngredientsConfirmed(dishes: DishWithSuggestions[]) {
    const confirmDishes = dishes
      .filter((d) => d.ingredients.length > 0)
      .map((d) => ({
        name: d.name,
        selling_price: d.price ?? 10.0,
        category: d.category,
        ingredients: d.ingredients.filter((i) => i.name.trim() && i.quantity > 0),
      }));

    confirmMutation.mutate(confirmDishes, {
      onSuccess: (data) => {
        setResult({ recipes: data.recipes_created, ingredients: data.ingredients_created });
        setStep(3);
      },
    });
  }

  return (
    <div>
      <Stepper currentStep={step} />

      {step === 0 && <StepPhoto onExtracted={handleExtracted} />}
      {step === 1 && (
        <StepDishes
          dishes={extractedDishes}
          onConfirm={handleDishesConfirmed}
          isLoading={suggestMutation.isPending}
        />
      )}
      {step === 2 && (
        <StepIngredients
          dishes={dishesWithIngredients}
          onConfirm={handleIngredientsConfirmed}
          isLoading={confirmMutation.isPending}
        />
      )}
      {step === 3 && result && (
        <StepDone recipesCreated={result.recipes} ingredientsCreated={result.ingredients} />
      )}
    </div>
  );
}
