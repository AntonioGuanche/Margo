import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, ExternalLink, Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import { usePlanInfo, openCustomerPortal } from '../hooks/useBilling';
import {
  useRestaurants,
  createSubRestaurant,
  switchRestaurant,
  updateRestaurant,
} from '../hooks/useRestaurants';
import { useQueryClient } from '@tanstack/react-query';

export default function Settings() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: planInfo } = usePlanInfo();
  const { data: restaurants, refetch: refetchRestaurants } = useRestaurants();
  const [editName, setEditName] = useState('');
  const [editMargin, setEditMargin] = useState('');
  const [editing, setEditing] = useState(false);
  const [newSubName, setNewSubName] = useState('');
  const [addingSub, setAddingSub] = useState(false);
  const [exportFrom, setExportFrom] = useState('');
  const [exportTo, setExportTo] = useState('');

  const plan = planInfo?.current_plan || 'free';
  const mainRestaurant = restaurants?.main;

  function startEdit() {
    if (mainRestaurant) {
      setEditName(mainRestaurant.name);
      setEditMargin(String(mainRestaurant.default_target_margin));
      setEditing(true);
    }
  }

  async function saveEdit() {
    if (!mainRestaurant) return;
    try {
      await updateRestaurant(mainRestaurant.id, {
        name: editName,
        default_target_margin: parseFloat(editMargin),
      });
      toast.success('Paramètres sauvegardés');
      setEditing(false);
      refetchRestaurants();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erreur');
    }
  }

  async function handlePortal() {
    try {
      const url = await openCustomerPortal();
      window.location.href = url;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erreur');
    }
  }

  async function handleAddSub() {
    if (!newSubName.trim()) return;
    setAddingSub(true);
    try {
      await createSubRestaurant(newSubName.trim());
      toast.success('Établissement ajouté');
      setNewSubName('');
      refetchRestaurants();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erreur');
    } finally {
      setAddingSub(false);
    }
  }

  async function handleSwitch(id: number) {
    try {
      const result = await switchRestaurant(id);
      localStorage.setItem('token', result.access_token);
      queryClient.invalidateQueries();
      toast.success(`Switché vers ${result.restaurant_name}`);
      navigate('/');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Erreur');
    }
  }

  function downloadCSV(endpoint: string, filename: string) {
    const token = localStorage.getItem('token');
    let url = `/api/export/${endpoint}`;
    if (endpoint === 'invoices' && (exportFrom || exportTo)) {
      const params = new URLSearchParams();
      if (exportFrom) params.set('from_date', exportFrom);
      if (exportTo) params.set('to_date', exportTo);
      url += `?${params.toString()}`;
    }

    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        a.click();
        URL.revokeObjectURL(a.href);
        toast.success('Export téléchargé');
      })
      .catch(() => toast.error("Erreur lors de l'export"));
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="text-stone-500 hover:text-stone-700">
          <ArrowLeft size={20} />
        </button>
        <h1 className="text-xl font-bold text-stone-900">Paramètres</h1>
      </div>

      {/* Profil */}
      <section className="bg-white rounded-xl border border-stone-200 p-4 space-y-3">
        <h2 className="font-semibold text-stone-900">Restaurant</h2>
        {editing ? (
          <div className="space-y-3">
            <div>
              <label className="text-sm text-stone-600">Nom</label>
              <input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full border border-stone-300 rounded-lg px-3 py-2 mt-1"
              />
            </div>
            <div>
              <label className="text-sm text-stone-600">Seuil de marge cible (%)</label>
              <input
                type="number"
                value={editMargin}
                onChange={(e) => setEditMargin(e.target.value)}
                className="w-full border border-stone-300 rounded-lg px-3 py-2 mt-1"
                min="0"
                max="100"
                step="0.5"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={saveEdit}
                className="bg-orange-700 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-orange-800"
              >
                Sauvegarder
              </button>
              <button
                onClick={() => setEditing(false)}
                className="text-stone-500 px-4 py-2 rounded-lg text-sm hover:bg-stone-100"
              >
                Annuler
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            <p className="text-stone-900 font-medium">{mainRestaurant?.name}</p>
            <p className="text-sm text-stone-500">{mainRestaurant?.owner_email}</p>
            <p className="text-sm text-stone-500">
              Marge cible : {mainRestaurant?.default_target_margin}%
            </p>
            <button
              onClick={startEdit}
              className="text-sm text-orange-700 hover:underline mt-1"
            >
              Modifier
            </button>
          </div>
        )}
      </section>

      {/* Abonnement */}
      <section className="bg-white rounded-xl border border-stone-200 p-4 space-y-3">
        <h2 className="font-semibold text-stone-900">Abonnement</h2>
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-0.5 rounded-full text-xs font-bold ${
              plan === 'free'
                ? 'bg-stone-100 text-stone-600'
                : plan === 'pro'
                ? 'bg-orange-100 text-orange-700'
                : 'bg-purple-100 text-purple-700'
            }`}
          >
            {plan.toUpperCase()}
          </span>
        </div>
        {planInfo && (
          <div className="text-sm text-stone-600 space-y-0.5">
            <p>
              Recettes : {planInfo.current_recipes}
              {planInfo.max_recipes !== null && ` / ${planInfo.max_recipes}`}
            </p>
            <p>
              Factures ce mois : {planInfo.current_invoices_this_month}
              {planInfo.max_invoices_per_month !== null &&
                ` / ${planInfo.max_invoices_per_month}`}
            </p>
          </div>
        )}
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => navigate('/pricing')}
            className="text-sm bg-orange-700 text-white px-4 py-2 rounded-lg font-medium hover:bg-orange-800"
          >
            Changer de plan
          </button>
          {planInfo?.can_manage_billing && (
            <button
              onClick={handlePortal}
              className="text-sm border border-stone-300 text-stone-700 px-4 py-2 rounded-lg hover:bg-stone-50 flex items-center gap-1"
            >
              Gérer mon abonnement
              <ExternalLink size={14} />
            </button>
          )}
        </div>
      </section>

      {/* Multi-établissement */}
      {plan === 'multi' && (
        <section className="bg-white rounded-xl border border-stone-200 p-4 space-y-3">
          <h2 className="font-semibold text-stone-900">Établissements</h2>
          <div className="space-y-2">
            {mainRestaurant && (
              <div className="flex items-center justify-between py-1.5 border-b border-stone-100">
                <span className="text-stone-900 font-medium">{mainRestaurant.name}</span>
                <span className="text-xs text-stone-400">Principal</span>
              </div>
            )}
            {restaurants?.sub_restaurants.map((sub) => (
              <div
                key={sub.id}
                className="flex items-center justify-between py-1.5 border-b border-stone-100"
              >
                <span className="text-stone-700">{sub.name}</span>
                <button
                  onClick={() => handleSwitch(sub.id)}
                  className="text-xs text-orange-700 hover:underline"
                >
                  Switcher
                </button>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              value={newSubName}
              onChange={(e) => setNewSubName(e.target.value)}
              placeholder="Nom du nouvel établissement"
              className="flex-1 border border-stone-300 rounded-lg px-3 py-2 text-sm"
            />
            <button
              onClick={handleAddSub}
              disabled={addingSub || !newSubName.trim()}
              className="bg-orange-700 text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-orange-800 disabled:opacity-50 flex items-center gap-1"
            >
              <Plus size={16} />
              Ajouter
            </button>
          </div>
        </section>
      )}

      {/* Export CSV */}
      <section className="bg-white rounded-xl border border-stone-200 p-4 space-y-3">
        <h2 className="font-semibold text-stone-900">Export CSV</h2>

        <div className="space-y-3">
          <div>
            <p className="text-sm text-stone-600 mb-2">Exporter les factures</p>
            <div className="flex gap-2 flex-wrap">
              <input
                type="date"
                value={exportFrom}
                onChange={(e) => setExportFrom(e.target.value)}
                className="border border-stone-300 rounded-lg px-3 py-1.5 text-sm"
              />
              <input
                type="date"
                value={exportTo}
                onChange={(e) => setExportTo(e.target.value)}
                className="border border-stone-300 rounded-lg px-3 py-1.5 text-sm"
              />
              <button
                onClick={() => downloadCSV('invoices', 'factures_export.csv')}
                className="flex items-center gap-1 text-sm border border-stone-300 text-stone-700 px-3 py-1.5 rounded-lg hover:bg-stone-50"
              >
                <Download size={14} />
                Télécharger
              </button>
            </div>
          </div>
          <div>
            <p className="text-sm text-stone-600 mb-2">Exporter les food costs</p>
            <button
              onClick={() => downloadCSV('food-costs', 'food_costs_export.csv')}
              className="flex items-center gap-1 text-sm border border-stone-300 text-stone-700 px-3 py-1.5 rounded-lg hover:bg-stone-50"
            >
              <Download size={14} />
              Télécharger les food costs
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
