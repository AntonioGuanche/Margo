import { useState } from 'react';
import toast from 'react-hot-toast';
import { Plus, Search, Pencil, Trash2, UtensilsCrossed, TrendingUp } from 'lucide-react';
import {
  useIngredients,
  useCreateIngredient,
  useUpdateIngredient,
  useDeleteIngredient,
} from '../hooks/useIngredients';
import type { Ingredient, UnitType } from '../hooks/useIngredients';
import IngredientForm from '../components/IngredientForm';
import PriceHistoryChart from '../components/PriceHistoryChart';
import ConfirmModal from '../components/ConfirmModal';
import { SkeletonList } from '../components/Skeleton';

const UNIT_LABELS: Record<UnitType, string> = {
  g: 'g',
  kg: 'kg',
  cl: 'cl',
  l: 'l',
  piece: 'pièce',
};

export default function Ingredients() {
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState<Ingredient | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [historyId, setHistoryId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<Ingredient | null>(null);

  const { data, isLoading } = useIngredients(search || undefined);
  const createMutation = useCreateIngredient();
  const updateMutation = useUpdateIngredient();
  const deleteMutation = useDeleteIngredient();

  function handleCreate(formData: {
    name: string;
    unit: UnitType;
    current_price?: number | null;
    supplier_name?: string | null;
  }) {
    createMutation.mutate(formData, {
      onSuccess: () => {
        setShowForm(false);
        toast.success('Ingrédient ajouté ✅');
      },
      onError: (err) => toast.error(err.message),
    });
  }

  function handleUpdate(formData: {
    name: string;
    unit: UnitType;
    current_price?: number | null;
    supplier_name?: string | null;
  }) {
    if (!editing) return;
    updateMutation.mutate(
      { id: editing.id, data: formData },
      {
        onSuccess: () => {
          setEditing(null);
          toast.success('Ingrédient modifié ✅');
        },
        onError: (err) => toast.error(err.message),
      },
    );
  }

  function handleDelete() {
    if (!deleting) return;
    deleteMutation.mutate(deleting.id, {
      onSuccess: () => {
        setDeleting(null);
        toast.success('Ingrédient supprimé');
      },
      onError: (err) => toast.error(err.message),
    });
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-stone-900 flex items-center gap-2">
          <UtensilsCrossed size={22} className="text-orange-700" />
          Ingrédients
        </h2>
        <button
          onClick={() => setShowForm(true)}
          className="bg-orange-700 text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-orange-800 transition-colors flex items-center gap-1"
        >
          <Plus size={16} />
          Ajouter
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search
          size={18}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400"
        />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full border border-stone-300 rounded-lg pl-10 pr-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
          placeholder="Rechercher un ingrédient..."
        />
      </div>

      {/* List */}
      {isLoading ? (
        <SkeletonList count={5} />
      ) : !data?.items.length ? (
        <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
          <UtensilsCrossed size={40} className="mx-auto text-stone-300 mb-3" />
          <p className="text-stone-600 font-medium mb-1">
            {search
              ? `Aucun ingrédient trouvé pour « ${search} »`
              : 'Aucun ingrédient'}
          </p>
          <p className="text-sm text-stone-400">
            {search ? '' : "Ajoute-en un ou importe une facture."}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {data.items.map((ingredient) => (
            <div key={ingredient.id}>
              <div className="bg-white rounded-xl border border-stone-200 px-4 py-3 flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-stone-900 truncate">
                    {ingredient.name}
                  </div>
                  <div className="text-sm text-stone-500 flex gap-3 mt-0.5">
                    <span>{UNIT_LABELS[ingredient.unit]}</span>
                    {ingredient.current_price != null && (
                      <span className="text-emerald-600 font-medium">
                        {ingredient.current_price.toFixed(2)} €/{UNIT_LABELS[ingredient.unit]}
                      </span>
                    )}
                    {ingredient.supplier_name && (
                      <span className="truncate">{ingredient.supplier_name}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 ml-2 shrink-0">
                  <button
                    onClick={() => setHistoryId(historyId === ingredient.id ? null : ingredient.id)}
                    className={`p-2 transition-colors ${historyId === ingredient.id ? 'text-orange-700' : 'text-stone-400 hover:text-orange-700'}`}
                    title="Historique des prix"
                  >
                    <TrendingUp size={16} />
                  </button>
                  <button
                    onClick={() => setEditing(ingredient)}
                    className="p-2 text-stone-400 hover:text-orange-700 transition-colors"
                    title="Modifier"
                  >
                    <Pencil size={16} />
                  </button>
                  <button
                    onClick={() => setDeleting(ingredient)}
                    className="p-2 text-stone-400 hover:text-red-600 transition-colors"
                    title="Supprimer"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              {historyId === ingredient.id && (
                <div className="mt-1 mb-2">
                  <PriceHistoryChart
                    ingredientId={ingredient.id}
                    onClose={() => setHistoryId(null)}
                  />
                </div>
              )}
            </div>
          ))}
          <p className="text-sm text-stone-400 text-center pt-2">
            {data.total} ingrédient{data.total > 1 ? 's' : ''}
          </p>
        </div>
      )}

      {/* Create modal */}
      {showForm && (
        <IngredientForm
          onSubmit={handleCreate}
          onClose={() => setShowForm(false)}
          isLoading={createMutation.isPending}
        />
      )}

      {/* Edit modal */}
      {editing && (
        <IngredientForm
          ingredient={editing}
          onSubmit={handleUpdate}
          onClose={() => setEditing(null)}
          isLoading={updateMutation.isPending}
        />
      )}

      {/* Delete confirmation */}
      {deleting && (
        <ConfirmModal
          title={`Supprimer « ${deleting.name} » ?`}
          message="Cette action est irréversible. Les recettes utilisant cet ingrédient seront affectées."
          onConfirm={handleDelete}
          onCancel={() => setDeleting(null)}
          isLoading={deleteMutation.isPending}
        />
      )}
    </div>
  );
}
