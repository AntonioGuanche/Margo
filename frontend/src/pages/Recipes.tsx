import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, BookOpen, Camera, ChevronDown, ChevronRight, Pencil, FileText, Upload, X, Loader2, Trash2 } from 'lucide-react';
import { useRecipes, useDeleteRecipe, useDeleteAllRecipes } from '../hooks/useRecipes';
import { useExtractMenu } from '../hooks/useOnboarding';
import { SkeletonList } from '../components/Skeleton';
import ConfirmModal from '../components/ConfirmModal';
import type { RecipeListItem } from '../hooks/useRecipes';

const STATUS_COLORS = {
  green: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
  orange: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
  red: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500' },
} as const;

const CATEGORY_ORDER = ['entrée', 'plat', 'dessert', 'boisson', 'autre'];

function groupByCategory(recipes: RecipeListItem[]) {
  const groups: Record<string, RecipeListItem[]> = {};
  for (const r of recipes) {
    const cat = r.category?.toLowerCase() || 'autre';
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(r);
  }
  return Object.entries(groups).sort(([a], [b]) => {
    const ia = CATEGORY_ORDER.indexOf(a);
    const ib = CATEGORY_ORDER.indexOf(b);
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
  });
}

function RecipeCard({ recipe, onClick, onDelete }: { recipe: RecipeListItem; onClick: () => void; onDelete: () => void }) {
  const colors = STATUS_COLORS[recipe.margin_status];
  return (
    <div className="w-full bg-white rounded-xl border border-stone-200 px-4 py-3 flex items-center justify-between group">
      <button
        onClick={onClick}
        className="min-w-0 flex-1 text-left hover:opacity-80 transition-opacity"
      >
        <div className="font-medium text-stone-900 truncate flex items-center gap-1.5">
          {recipe.name}
          <span className={`text-xs px-1.5 py-0.5 rounded-full ${
            recipe.is_homemade
              ? 'bg-orange-50 text-orange-700'
              : 'bg-stone-100 text-stone-500'
          }`}>
            {recipe.is_homemade ? 'Maison' : 'Acheté'}
          </span>
        </div>
        <div className="text-sm text-stone-500 flex gap-3 mt-0.5">
          <span>{recipe.selling_price.toFixed(2)} €</span>
        </div>
      </button>
      <div className="flex items-center gap-2 ml-2 shrink-0">
        {recipe.food_cost_percent != null && (
          <span className={`text-sm font-semibold ${colors.text}`}>
            {recipe.food_cost_percent.toFixed(1)}%
          </span>
        )}
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="p-1.5 text-stone-300 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-all"
          title="Supprimer"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}

export default function Recipes() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const { data, isLoading } = useRecipes(search || undefined);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [showUploadZone, setShowUploadZone] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const extractMutation = useExtractMenu();
  const deleteOneMutation = useDeleteRecipe();
  const deleteAllMutation = useDeleteAllRecipes();
  const [deleting, setDeleting] = useState<RecipeListItem | null>(null);
  const [showDeleteAll, setShowDeleteAll] = useState(false);
  const [deleteAllConfirm, setDeleteAllConfirm] = useState('');

  function handleDeleteOne(id: number) {
    deleteOneMutation.mutate(id, {
      onSuccess: () => setDeleting(null),
    });
  }

  function handleDeleteAll() {
    deleteAllMutation.mutate(undefined, {
      onSuccess: () => {
        setShowDeleteAll(false);
        setDeleteAllConfirm('');
      },
    });
  }

  function handleMenuFile(file: File) {
    extractMutation.mutate(file, {
      onSuccess: (data) => {
        navigate('/onboarding', { state: { dishes: data.dishes, skipExtract: true } });
      },
    });
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleMenuFile(file);
  };

  const recipes = data?.items ?? [];
  const grouped = groupByCategory(recipes);

  const toggleCategory = (cat: string) => {
    setCollapsed((prev) => ({ ...prev, [cat]: !prev[cat] }));
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-semibold text-stone-900 flex items-center gap-2">
            <BookOpen size={22} className="text-orange-700" />
            Ma carte
          </h2>
        </div>
        <button
          onClick={() => setShowUploadZone(!showUploadZone)}
          className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1 ${
            showUploadZone
              ? 'bg-stone-200 text-stone-700 hover:bg-stone-300'
              : 'bg-orange-700 text-white hover:bg-orange-800'
          }`}
        >
          {showUploadZone ? (
            <>
              <X size={16} />
              Fermer
            </>
          ) : (
            <>
              <Plus size={16} />
              Ajouter
            </>
          )}
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full border border-stone-300 rounded-lg pl-10 pr-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
          placeholder="Rechercher un plat..."
        />
      </div>

      {/* Upload zone (inline, toggleable) */}
      {showUploadZone && (
        <div className="mb-4 space-y-3">
          {extractMutation.isPending ? (
            <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
              <Loader2 size={40} className="text-orange-700 animate-spin mx-auto mb-3" />
              <p className="text-stone-600 font-medium">Extraction des plats en cours...</p>
              <p className="text-sm text-stone-400 mt-1">L'IA analyse votre carte</p>
            </div>
          ) : (
            <div
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors ${
                isDragging ? 'border-orange-500 bg-orange-50' : 'border-stone-300 bg-white'
              }`}
            >
              <FileText size={36} className="mx-auto text-stone-300 mb-2" />
              <p className="text-stone-600 font-medium mb-1">Glisse ta carte ici</p>
              <p className="text-sm text-stone-400 mb-3">PDF ou image de ton menu</p>
              <div className="flex items-center justify-center gap-3">
                <label className="inline-flex items-center gap-2 bg-orange-700 text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-orange-800 cursor-pointer transition-colors">
                  <Upload size={16} />
                  Choisir un fichier
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".jpg,.jpeg,.png,.webp,.pdf"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleMenuFile(e.target.files[0])}
                  />
                </label>
                <label className="inline-flex items-center gap-2 bg-white text-stone-700 px-4 py-2 rounded-xl text-sm font-medium border border-stone-300 hover:border-stone-400 cursor-pointer transition-colors">
                  <Camera size={16} />
                  Photo
                  <input
                    ref={cameraInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleMenuFile(e.target.files[0])}
                  />
                </label>
              </div>
            </div>
          )}

          {/* Separator */}
          <div className="flex items-center gap-3">
            <div className="flex-1 border-t border-stone-200" />
            <span className="text-xs text-stone-400">ou</span>
            <div className="flex-1 border-t border-stone-200" />
          </div>

          {/* Manual add button */}
          <button
            onClick={() => navigate('/recipes/new')}
            className="w-full bg-white border border-stone-200 rounded-xl px-4 py-3 flex items-center gap-3 hover:bg-stone-50 transition-colors"
          >
            <Pencil size={18} className="text-stone-500" />
            <div className="text-left">
              <p className="text-sm font-medium text-stone-900">Ajouter un plat manuellement</p>
              <p className="text-xs text-stone-500">Nom, prix, catégorie et ingrédients</p>
            </div>
          </button>

          {extractMutation.isError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
              {extractMutation.error.message}
            </div>
          )}
        </div>
      )}

      {/* List grouped by category */}
      {isLoading ? (
        <SkeletonList count={5} />
      ) : recipes.length === 0 ? (
        <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
          <BookOpen size={40} className="mx-auto text-stone-300 mb-3" />
          <p className="text-stone-600 font-medium mb-1">
            {search
              ? `Aucun plat trouvé pour « ${search} »`
              : 'Aucun plat sur ta carte'}
          </p>
          {!search && (
            <>
              <p className="text-sm text-stone-400 mb-4">
                Commence par photographier ta carte !
              </p>
              <button
                onClick={() => setShowUploadZone(true)}
                className="bg-orange-700 text-white px-4 py-2.5 rounded-xl text-sm font-medium hover:bg-orange-800 transition-colors inline-flex items-center gap-2"
              >
                <Camera size={16} />
                Photographier ma carte
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {grouped.map(([category, items], idx) => {
            const isCollapsed = collapsed[category] ?? (idx > 0);
            const avgCost =
              items.filter((r) => r.food_cost_percent != null).length > 0
                ? items
                    .filter((r) => r.food_cost_percent != null)
                    .reduce((sum, r) => sum + (r.food_cost_percent ?? 0), 0) /
                  items.filter((r) => r.food_cost_percent != null).length
                : null;

            return (
              <div key={category}>
                <button
                  onClick={() => toggleCategory(category)}
                  className="flex items-center gap-2 w-full text-left mb-2"
                >
                  {isCollapsed ? (
                    <ChevronRight size={14} className="text-stone-400" />
                  ) : (
                    <ChevronDown size={14} className="text-stone-400" />
                  )}
                  <span className="text-xs font-semibold text-stone-500 uppercase tracking-wide">
                    {category} ({items.length})
                  </span>
                  {avgCost != null && (
                    <span className="text-xs text-stone-400">
                      — moy. {avgCost.toFixed(1)}%
                    </span>
                  )}
                </button>

                {!isCollapsed && (
                  <div className="space-y-2">
                    {items.map((recipe) => (
                      <RecipeCard
                        key={recipe.id}
                        recipe={recipe}
                        onClick={() => navigate(`/recipes/${recipe.id}`)}
                        onDelete={() => setDeleting(recipe)}
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
          <p className="text-sm text-stone-400 text-center pt-2">
            {data?.total ?? 0} plat{(data?.total ?? 0) > 1 ? 's' : ''}
          </p>

          {data && data.items.length > 0 && (
            <button
              onClick={() => setShowDeleteAll(true)}
              className="text-xs text-stone-400 hover:text-red-500 transition-colors mt-4 flex items-center gap-1 mx-auto"
            >
              <Trash2 size={12} />
              Supprimer tout le menu
            </button>
          )}
        </div>
      )}

      {/* Modal suppression individuelle */}
      {deleting && (
        <ConfirmModal
          title={`Supprimer « ${deleting.name} » ?`}
          message="Cette action est irréversible. Le plat et ses ingrédients associés seront supprimés."
          onConfirm={() => handleDeleteOne(deleting.id)}
          onCancel={() => setDeleting(null)}
          isLoading={deleteOneMutation.isPending}
        />
      )}

      {/* Modal suppression totale */}
      {showDeleteAll && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 max-w-sm w-full space-y-4">
            <h3 className="text-lg font-semibold text-stone-900">Supprimer tout le menu ?</h3>
            <p className="text-sm text-stone-600">
              Cette action supprimera les <strong>{data?.total ?? 0} recettes</strong> et ne peut pas être annulée.
            </p>
            <p className="text-sm text-stone-600">
              Tapez <strong>SUPPRIMER</strong> pour confirmer :
            </p>
            <input
              type="text"
              value={deleteAllConfirm}
              onChange={(e) => setDeleteAllConfirm(e.target.value)}
              className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
              placeholder="SUPPRIMER"
            />
            <div className="flex gap-3">
              <button
                onClick={() => { setShowDeleteAll(false); setDeleteAllConfirm(''); }}
                className="flex-1 bg-stone-100 text-stone-700 py-2 rounded-lg text-sm font-medium hover:bg-stone-200"
              >
                Annuler
              </button>
              <button
                onClick={handleDeleteAll}
                disabled={deleteAllConfirm !== 'SUPPRIMER' || deleteAllMutation.isPending}
                className="flex-1 bg-red-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
              >
                {deleteAllMutation.isPending ? 'Suppression...' : 'Confirmer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
