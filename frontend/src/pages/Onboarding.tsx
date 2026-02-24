import { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Camera, Upload, Plus, Trash2, Check, ChevronDown, ChevronUp, FileText, Loader2, CopyPlus, ShoppingCart } from 'lucide-react';
import {
  useExtractMenu,
  useSuggestIngredients,
  useConfirmOnboarding,
} from '../hooks/useOnboarding';
import type { ExtractedDish, DishWithSuggestions } from '../hooks/useOnboarding';

const CATEGORIES = ['entrée', 'plat', 'dessert', 'cocktail', 'boisson', 'autre'];
const UNITS = ['g', 'kg', 'cl', 'l', 'piece'];

const COCKTAIL_NAMES = new Set([
  'mojito', 'cuba libre', 'sex on the beach', 'cosmopolitan',
  'margarita', 'daiquiri', 'caipirinha', 'pina colada', 'piña colada',
  'tequila sunrise', 'long island', 'gin tonic', 'gin & tonic',
  'vodka tonic', 'whisky coca', 'rhum coca', 'moscow mule',
  'spritz', 'aperol spritz', 'hugo', 'negroni',
  'old fashioned', 'manhattan', 'bloody mary', 'mimosa', 'bellini',
  'kir', 'kir royal', 'kir royale', 'irish coffee', 'espresso martini',
  'sangria', 'punch', 'planteur', 'ti punch',
  'tom collins', 'whisky sour', 'mai tai', 'blue lagoon',
  'paloma', 'sidecar', 'french 75', 'cuba',
]);

const COCKTAIL_KEYWORDS = ['cocktail', 'mocktail', 'virgin', 'spritz', 'sour', 'mule', 'fizz', 'collins', 'punch', 'sangria'];

function isCocktail(name: string): boolean {
  const lower = name.toLowerCase().trim();
  for (const c of COCKTAIL_NAMES) {
    if (lower.includes(c)) return true;
  }
  for (const kw of COCKTAIL_KEYWORDS) {
    if (lower.includes(kw)) return true;
  }
  return false;
}

function Stepper({ currentStep }: { currentStep: number }) {
  const steps = ['Menu', 'Plats', 'Ingrédients', 'Terminé'];
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

// ----- Step 1: Menu (drag & drop / photo / file picker — auto-extract) -----
function StepMenu({
  onExtracted,
}: {
  onExtracted: (dishes: ExtractedDish[], imageSrc: string) => void;
}) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const extractMutation = useExtractMenu();

  const processFile = useCallback(
    (f: File) => {
      // Auto-extract immediately
      extractMutation.mutate(f, {
        onSuccess: (data) => {
          // Generate preview for images, use placeholder for PDFs
          if (f.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => onExtracted(data.dishes, e.target?.result as string);
            reader.readAsDataURL(f);
          } else {
            onExtracted(data.dishes, '');
          }
        },
      });
    },
    [extractMutation, onExtracted],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) processFile(f);
    },
    [processFile],
  );

  // Loading state
  if (extractMutation.isPending) {
    return (
      <div className="space-y-4 text-center py-8">
        <Loader2 size={48} className="text-orange-700 animate-spin mx-auto" />
        <h3 className="text-lg font-semibold text-stone-900">Extraction en cours...</h3>
        <p className="text-sm text-stone-500">L'IA analyse votre carte et extrait les plats</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-stone-900 text-center">
        Importez votre carte
      </h3>
      <p className="text-sm text-stone-500 text-center">
        Photo, PDF ou image — l'IA extrait les plats automatiquement
      </p>

      {/* Drag & drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
          isDragging ? 'border-orange-500 bg-orange-50' : 'border-stone-300 bg-white'
        }`}
      >
        <FileText size={40} className="mx-auto text-stone-300 mb-3" />
        <p className="text-stone-600 font-medium mb-1">Glissez votre carte ici</p>
        <p className="text-sm text-stone-400 mb-4">Image (JPEG, PNG) ou PDF</p>

        <label className="inline-flex items-center gap-2 bg-orange-700 text-white px-6 py-3 rounded-xl font-medium hover:bg-orange-800 transition-colors cursor-pointer">
          <Upload size={18} />
          Choisir un fichier
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,.pdf"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && processFile(e.target.files[0])}
          />
        </label>
      </div>

      {/* Camera option */}
      <button
        onClick={() => cameraInputRef.current?.click()}
        className="w-full bg-white text-stone-700 py-3 rounded-xl font-medium border border-stone-300 hover:border-stone-400 transition-colors flex items-center justify-center gap-2"
      >
        <Camera size={18} />
        Photographier ma carte
      </button>
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && processFile(e.target.files[0])}
      />

      {extractMutation.isError && (
        <p className="text-red-600 text-sm text-center">
          {extractMutation.error.message}
        </p>
      )}
    </div>
  );
}

// ----- Step 2: Review dishes -----
type DishWithHomemade = ExtractedDish & { is_homemade: boolean };

function StepDishes({
  dishes,
  onConfirm,
  isLoading,
}: {
  dishes: ExtractedDish[];
  onConfirm: (dishes: DishWithHomemade[]) => void;
  isLoading: boolean;
}) {
  const [editableDishes, setEditableDishes] = useState(
    dishes.map((d) => {
      const cat = (d.category ?? '').toLowerCase();
      // Cocktails and cocktail category → homemade (has sub-ingredients)
      // Boissons (non-cocktail) → purchased
      // Entrée, plat, dessert → homemade
      // Autre → purchased by default
      const isHomemade = cat === 'cocktail'
        ? true
        : cat === 'boisson'
          ? isCocktail(d.name)
          : ['entrée', 'plat', 'dessert'].includes(cat) || (!cat && true);
      return {
        ...d,
        selected: true,
        is_homemade: isHomemade,
      };
    }),
  );

  function updateDish(index: number, updates: Partial<ExtractedDish & { selected: boolean; is_homemade: boolean }>) {
    setEditableDishes((prev) =>
      prev.map((d, i) => (i === index ? { ...d, ...updates } : d)),
    );
  }

  function addDish() {
    setEditableDishes((prev) => [
      ...prev,
      { name: '', price: null, category: 'plat', selected: true, is_homemade: true },
    ]);
  }

  function duplicateDish(index: number) {
    setEditableDishes((prev) => {
      const source = prev[index];
      const copy = {
        ...source,
        name: '',
        selected: true,
      };
      const next = [...prev];
      next.splice(index + 1, 0, copy);
      return next;
    });
    // Focus the name input of the new line
    setTimeout(() => {
      const inputs = document.querySelectorAll<HTMLInputElement>('[data-dish-name]');
      inputs[index + 1]?.focus();
    }, 50);
  }

  function handleConfirm() {
    const selected = editableDishes
      .filter((d) => d.selected && d.name.trim())
      .map(({ name, price, category, is_homemade }) => ({ name: name.trim(), price, category, is_homemade }));
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
                data-dish-name
                value={dish.name}
                onChange={(e) => updateDish(index, { name: e.target.value })}
                className="flex-1 border border-stone-300 rounded-lg px-2 py-1.5 text-sm text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
                placeholder="Nom du plat"
              />
              <button
                onClick={() => duplicateDish(index)}
                className="p-1 text-stone-400 hover:text-orange-700 transition-colors"
                title="Dupliquer ce plat"
              >
                <CopyPlus size={16} />
              </button>
            </div>
            <div className="flex gap-2 ml-6">
              <div className="relative w-24">
                <input
                  type="number"
                  value={dish.price ?? ''}
                  onChange={(e) =>
                    updateDish(index, { price: e.target.value ? parseFloat(e.target.value) : null })
                  }
                  className="w-full border border-stone-300 rounded-lg px-2 py-1.5 pr-7 text-sm text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
                  placeholder="Prix"
                  step="0.50"
                  inputMode="decimal"
                />
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-sm text-stone-400 pointer-events-none">€</span>
              </div>
              <select
                value={dish.category ?? 'plat'}
                onChange={(e) => {
                  const cat = e.target.value.toLowerCase();
                  const homemade = cat === 'cocktail'
                    ? true
                    : cat === 'boisson'
                      ? isCocktail(dish.name)
                      : ['entrée', 'plat', 'dessert'].includes(cat);
                  updateDish(index, {
                    category: e.target.value,
                    is_homemade: homemade,
                  });
                }}
                className="flex-1 border border-stone-300 rounded-lg px-2 py-1.5 text-sm text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-1.5 ml-6 mt-1">
              <input
                type="checkbox"
                checked={dish.is_homemade}
                onChange={(e) => updateDish(index, { is_homemade: e.target.checked })}
                className="w-3.5 h-3.5 accent-orange-700"
              />
              <span className="text-xs text-stone-500">Maison (avec sous-ingrédients)</span>
            </label>
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
                {dish.is_homemade ? (
                  <span className="text-sm text-stone-500 ml-2">
                    {dish.ingredients.length} ingrédient{dish.ingredients.length > 1 ? 's' : ''}
                  </span>
                ) : (
                  <span className="text-sm text-emerald-600 ml-2">Acheté</span>
                )}
              </div>
              {openIndex === dishIdx ? (
                <ChevronUp size={18} className="text-stone-400" />
              ) : (
                <ChevronDown size={18} className="text-stone-400" />
              )}
            </button>

            {/* Accordion body */}
            {openIndex === dishIdx && (
              <div className="px-4 pb-3 border-t border-stone-100 pt-3">
                {!dish.is_homemade ? (
                  <div className="flex items-center gap-2 text-sm text-stone-500">
                    <ShoppingCart size={14} />
                    <span>Produit acheté — l'ingrédient « {dish.name} » sera créé automatiquement</span>
                  </div>
                ) : (
                  <div className="space-y-2">
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
  const location = useLocation();
  const passedState = location.state as {
    dishes?: ExtractedDish[];
    skipExtract?: boolean;
    file?: File;
  } | null;

  const [step, setStep] = useState(passedState?.skipExtract ? 1 : 0);
  const [extractedDishes, setExtractedDishes] = useState<ExtractedDish[]>(
    passedState?.dishes ?? [],
  );
  const [dishesHomemadeMap, setDishesHomemadeMap] = useState<Record<string, boolean>>({});
  const [dishesWithIngredients, setDishesWithIngredients] = useState<DishWithSuggestions[]>([]);
  const [result, setResult] = useState<{ recipes: number; ingredients: number } | null>(null);

  const suggestMutation = useSuggestIngredients();
  const confirmMutation = useConfirmOnboarding();
  const autoExtractMutation = useExtractMenu();

  // Auto-extract if file passed from Ma Carte (without pre-extracted dishes)
  useEffect(() => {
    if (passedState?.file && !passedState?.skipExtract && step === 0) {
      autoExtractMutation.mutate(passedState.file, {
        onSuccess: (data) => {
          setExtractedDishes(data.dishes);
          setStep(1);
        },
      });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleExtracted(dishes: ExtractedDish[]) {
    setExtractedDishes(dishes);
    setStep(1);
  }

  function handleDishesConfirmed(dishes: DishWithHomemade[]) {
    // Store is_homemade mapping for later
    const homemadeMap: Record<string, boolean> = {};
    for (const d of dishes) {
      homemadeMap[d.name] = d.is_homemade;
    }
    setDishesHomemadeMap(homemadeMap);

    // Separate homemade from purchased
    const homemadeDishes = dishes.filter((d) => d.is_homemade);
    const boughtDishes = dishes.filter((d) => !d.is_homemade);

    // Pre-fill purchased items: ingredient = product name, qty 1, unit piece
    const purchasedWithIngredients: DishWithSuggestions[] = boughtDishes.map((d) => ({
      name: d.name,
      price: d.price,
      category: d.category,
      is_homemade: false,
      ingredients: [{ name: d.name, quantity: 1, unit: 'piece' }],
    }));

    if (homemadeDishes.length > 0) {
      // Get AI suggestions for homemade dishes only
      suggestMutation.mutate(homemadeDishes, {
        onSuccess: (data) => {
          const allDishes: DishWithSuggestions[] = [
            ...data.dishes.map((d) => ({ ...d, is_homemade: true })),
            ...purchasedWithIngredients,
          ];
          setDishesWithIngredients(allDishes);
          setStep(2);
        },
      });
    } else {
      // All purchased — skip AI suggestions entirely
      setDishesWithIngredients(purchasedWithIngredients);
      setStep(2);
    }
  }

  function handleIngredientsConfirmed(dishes: DishWithSuggestions[]) {
    const confirmDishes = dishes
      .filter((d) => d.is_homemade ? d.ingredients.length > 0 : true)
      .map((d) => ({
        name: d.name,
        selling_price: d.price ?? 10.0,
        category: d.category,
        is_homemade: d.is_homemade ?? dishesHomemadeMap[d.name] ?? true,
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

      {step === 0 && (autoExtractMutation.isPending ? (
        <div className="space-y-4 text-center py-8">
          <Loader2 size={48} className="text-orange-700 animate-spin mx-auto" />
          <h3 className="text-lg font-semibold text-stone-900">Extraction en cours...</h3>
          <p className="text-sm text-stone-500">L'IA analyse votre carte et extrait les plats</p>
        </div>
      ) : (
        <StepMenu onExtracted={handleExtracted} />
      ))}
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
