import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import type { Ingredient, UnitType } from '../hooks/useIngredients';

const UNITS: { value: UnitType; label: string }[] = [
  { value: 'kg', label: 'kg' },
  { value: 'g', label: 'g' },
  { value: 'l', label: 'l' },
  { value: 'cl', label: 'cl' },
  { value: 'piece', label: 'pièce' },
];

const CATEGORIES = [
  { value: '', label: 'Non catégorisé' },
  { value: 'boissons', label: 'Boissons' },
  { value: 'viandes & poissons', label: 'Viandes & poissons' },
  { value: 'fruits & légumes', label: 'Fruits & légumes' },
  { value: 'produits laitiers', label: 'Produits laitiers' },
  { value: 'épicerie & sec', label: 'Épicerie & sec' },
  { value: 'surgelés', label: 'Surgelés' },
  { value: 'autre', label: 'Autre' },
];

interface IngredientFormProps {
  ingredient?: Ingredient | null;
  onSubmit: (data: {
    name: string;
    unit: UnitType;
    current_price?: number | null;
    supplier_name?: string | null;
    category?: string | null;
  }) => void;
  onClose: () => void;
  isLoading?: boolean;
}

export default function IngredientForm({
  ingredient,
  onSubmit,
  onClose,
  isLoading,
}: IngredientFormProps) {
  const [name, setName] = useState('');
  const [unit, setUnit] = useState<UnitType>('kg');
  const [price, setPrice] = useState('');
  const [supplier, setSupplier] = useState('');
  const [category, setCategory] = useState('');

  useEffect(() => {
    if (ingredient) {
      setName(ingredient.name);
      setUnit(ingredient.unit);
      setPrice(ingredient.current_price?.toString() ?? '');
      setSupplier(ingredient.supplier_name ?? '');
      setCategory(ingredient.category ?? '');
    }
  }, [ingredient]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      name: name.trim(),
      unit,
      current_price: price ? parseFloat(price) : null,
      supplier_name: supplier.trim() || null,
      category: category || null,
    });
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50">
      <div className="bg-white w-full sm:max-w-md sm:rounded-xl rounded-t-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-stone-900">
            {ingredient ? 'Modifier l\'ingrédient' : 'Nouvel ingrédient'}
          </h2>
          <button onClick={onClose} className="text-stone-400 hover:text-stone-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">
              Nom
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-stone-300 rounded-lg px-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
              placeholder="Ex: Tomates cerises"
              required
              autoFocus
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">
                Unité
              </label>
              <select
                value={unit}
                onChange={(e) => setUnit(e.target.value as UnitType)}
                className="w-full border border-stone-300 rounded-lg px-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
              >
                {UNITS.map((u) => (
                  <option key={u.value} value={u.value}>
                    {u.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-stone-700 mb-1">
                Catégorie
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full border border-stone-300 rounded-lg px-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
              >
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">
              Prix actuel (€)
            </label>
            <input
              type="number"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              className="w-full border border-stone-300 rounded-lg px-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
              placeholder="0.00"
              step="0.01"
              min="0"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">
              Fournisseur
            </label>
            <input
              type="text"
              value={supplier}
              onChange={(e) => setSupplier(e.target.value)}
              className="w-full border border-stone-300 rounded-lg px-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
              placeholder="Ex: Metro"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !name.trim()}
            className="w-full bg-orange-700 text-white py-2.5 rounded-lg font-medium hover:bg-orange-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Enregistrement...' : ingredient ? 'Modifier' : 'Ajouter'}
          </button>
        </form>
      </div>
    </div>
  );
}
