import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, BookOpen, ChevronDown, ChevronRight, X, Trash2 } from 'lucide-react';
import { useRecipes, useDeleteRecipe, useDeleteAllRecipes } from '../hooks/useRecipes';
import { SkeletonList } from '../components/Skeleton';
import ConfirmModal from '../components/ConfirmModal';
import MenuUploadZone from '../components/MenuUploadZone';
import { STATUS_COLORS } from '../utils/colors';
import type { RecipeListItem } from '../types';

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
          className="p-1.5 text-stone-300 hover:text-red-600 md:opacity-0 md:group-hover:opacity-100 transition-all"
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
  const [sortBy, setSortBy] = useState<'category' | 'food_cost'>('category');
  const { data, isLoading } = useRecipes(search || undefined);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [showUploadZone, setShowUploadZone] = useState(false);

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

  const recipes = data?.items ?? [];
  const isEmpty = !isLoading && !recipes.length && !search;

  useEffect(() => {
    if (isEmpty) setShowUploadZone(true);
  }, [isEmpty]);

  const grouped = groupByCategory(recipes);
  const sortedByFoodCost = sortBy === 'food_cost'
    ? [...recipes].sort((a, b) => (b.food_cost_percent ?? 0) - (a.food_cost_percent ?? 0))
    : null;

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
        {!isEmpty && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSortBy(sortBy === 'category' ? 'food_cost' : 'category')}
              className="text-xs text-stone-500 hover:text-orange-700 border border-stone-200 rounded-lg px-2.5 py-1.5 transition-colors"
            >
              {sortBy === 'category' ? '↕ Trier par food cost' : '↕ Trier par catégorie'}
            </button>
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
        )}
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
        <div className="mb-4">
          <MenuUploadZone
            onExtracted={(dishes) =>
              navigate('/onboarding', { state: { dishes, skipExtract: true } })
            }
          />
        </div>
      )}

      {/* List grouped by category */}
      {isLoading ? (
        <SkeletonList count={5} />
      ) : recipes.length === 0 && search ? (
        <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
          <BookOpen size={40} className="mx-auto text-stone-300 mb-3" />
          <p className="text-stone-600 font-medium mb-1">
            Aucun plat trouvé pour « {search} »
          </p>
        </div>
      ) : recipes.length > 0 ? (
        <div className="space-y-4">
          {sortBy === 'category' ? (
            // Grouped by category
            <>
              {grouped.map(([category, items]) => {
                const isCollapsed = collapsed[category] ?? false;
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
            </>
          ) : (
            // Flat list sorted by food cost
            <div className="space-y-2">
              {sortedByFoodCost!.map((recipe) => (
                <RecipeCard
                  key={recipe.id}
                  recipe={recipe}
                  onClick={() => navigate(`/recipes/${recipe.id}`)}
                  onDelete={() => setDeleting(recipe)}
                />
              ))}
            </div>
          )}

          <p className="text-sm text-stone-400 text-center pt-2">
            {data?.total ?? 0} plat{(data?.total ?? 0) > 1 ? 's' : ''}
          </p>
          {data && data.total > data.items.length && (
            <p className="text-xs text-amber-600 text-center mt-2">
              Affichage de {data.items.length} sur {data.total}. Utilise la recherche pour affiner.
            </p>
          )}

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
      ) : null}

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
