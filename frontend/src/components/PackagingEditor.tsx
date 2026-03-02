import { useState } from 'react';
import { Package, Pencil, X } from 'lucide-react';

interface PackagingEditorProps {
  /** Auto-detected units (from backend units_per_package or parse_packaging_volume) */
  detectedUnits: number | null;
  /** Auto-detected cl per unit (from backend volume info) */
  detectedClPerUnit: number | null;
  /** Auto-detected total volume in liters */
  detectedVolumeLiters: number | null;
  /** User overrides */
  packagingUnits: number | null;
  packagingClPerUnit: number | null;
  /** Total price of the line (for €/l calculation) */
  totalPrice: number | null;
  /** Quantity on the line */
  quantity: number | null;
  /** Callback to update LineState */
  onChange: (updates: {
    packaging_units: number | null;
    packaging_cl_per_unit: number | null;
    volume_liters: number | null;
  }) => void;
}

export default function PackagingEditor({
  detectedUnits,
  detectedClPerUnit,
  detectedVolumeLiters,
  packagingUnits,
  packagingClPerUnit,
  totalPrice,
  quantity,
  onChange,
}: PackagingEditorProps) {
  // Effective values: user override > detected
  const units = packagingUnits ?? detectedUnits;
  const clPerUnit = packagingClPerUnit ?? detectedClPerUnit;

  const [isEditing, setIsEditing] = useState(false);
  const [editUnits, setEditUnits] = useState<string>(units?.toString() ?? '');
  const [editCl, setEditCl] = useState<string>(clPerUnit?.toString() ?? '');

  // Calculate derived values
  const effectiveVolumeLiters = units && clPerUnit
    ? Math.round(units * clPerUnit / 100 * 10000) / 10000
    : detectedVolumeLiters;

  const pricePerLiter = effectiveVolumeLiters && totalPrice && quantity
    ? Math.abs(totalPrice) / (Math.abs(quantity) * effectiveVolumeLiters)
    : null;

  const hasPackaging = units != null && units > 0;
  const hasVolume = effectiveVolumeLiters != null && effectiveVolumeLiters > 0;

  function handleSave() {
    const u = editUnits ? parseInt(editUnits) : null;
    const cl = editCl ? parseInt(editCl) : null;
    const vol = u && cl ? Math.round(u * cl / 100 * 10000) / 10000 : null;
    onChange({
      packaging_units: u,
      packaging_cl_per_unit: cl,
      volume_liters: vol,
    });
    setIsEditing(false);
  }

  function handleClear() {
    onChange({
      packaging_units: null,
      packaging_cl_per_unit: null,
      volume_liters: detectedVolumeLiters,  // revert to auto-detected
    });
    setEditUnits(detectedUnits?.toString() ?? '');
    setEditCl(detectedClPerUnit?.toString() ?? '');
    setIsEditing(false);
  }

  // --- Not editing: show summary or "add" button ---
  if (!isEditing) {
    if (hasPackaging && hasVolume) {
      // Show detected/set packaging info
      return (
        <div className="text-xs bg-blue-50 border border-blue-100 rounded-lg px-3 py-2 mt-1.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-blue-700">
              <Package size={13} />
              <span>
                <strong>{units} × {clPerUnit}cl</strong>
                {' = '}
                {effectiveVolumeLiters?.toFixed(2)}L
                {pricePerLiter != null && (
                  <> → <strong>{pricePerLiter.toFixed(2)} €/l</strong></>
                )}
              </span>
            </div>
            <button
              onClick={() => {
                setEditUnits(units?.toString() ?? '');
                setEditCl(clPerUnit?.toString() ?? '');
                setIsEditing(true);
              }}
              className="text-blue-500 hover:text-blue-700 p-0.5"
              title="Modifier le conditionnement"
            >
              <Pencil size={12} />
            </button>
          </div>
          {packagingUnits == null && detectedUnits != null && (
            <p className="text-[10px] text-blue-400 mt-0.5">Détecté automatiquement</p>
          )}
          {packagingUnits != null && (
            <p className="text-[10px] text-blue-400 mt-0.5">Modifié manuellement</p>
          )}
        </div>
      );
    }

    if (hasPackaging && !hasVolume) {
      // Has units but no cl info — prompt user
      return (
        <div className="text-xs bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 mt-1.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-amber-700">
              <Package size={13} />
              <span>
                {units} unités détectées — <strong>cl par unité ?</strong>
              </span>
            </div>
            <button
              onClick={() => {
                setEditUnits(units?.toString() ?? '');
                setEditCl('');
                setIsEditing(true);
              }}
              className="text-amber-600 hover:text-amber-800 text-[11px] font-medium underline"
            >
              Compléter
            </button>
          </div>
        </div>
      );
    }

    // No packaging detected — show discreet "add" button
    return (
      <button
        onClick={() => {
          setEditUnits('');
          setEditCl('');
          setIsEditing(true);
        }}
        className="text-[11px] text-stone-400 hover:text-stone-600 mt-1 flex items-center gap-1"
      >
        <Package size={11} />
        Ajouter un conditionnement
      </button>
    );
  }

  // --- Editing mode ---
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 mt-1.5 space-y-2">
      <div className="flex items-center gap-1.5 text-xs text-blue-700 font-medium">
        <Package size={13} />
        Conditionnement
      </div>
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1">
          <input
            type="number"
            value={editUnits}
            onChange={(e) => setEditUnits(e.target.value)}
            placeholder="Nb"
            min="1"
            max="100"
            className="w-14 border border-blue-200 rounded px-1.5 py-1 text-xs text-center focus:outline-none focus:ring-1 focus:ring-blue-400"
            autoFocus
          />
          <span className="text-xs text-stone-500">×</span>
          <input
            type="number"
            value={editCl}
            onChange={(e) => setEditCl(e.target.value)}
            placeholder="cl"
            min="1"
            max="200"
            className="w-14 border border-blue-200 rounded px-1.5 py-1 text-xs text-center focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
          <span className="text-xs text-stone-500">cl</span>
        </div>

        {/* Preview */}
        {editUnits && editCl && (
          <span className="text-xs text-blue-600">
            = {(parseInt(editUnits) * parseInt(editCl) / 100).toFixed(2)}L
            {totalPrice != null && quantity != null && quantity !== 0 && (
              <> → {(Math.abs(totalPrice) / (Math.abs(quantity) * parseInt(editUnits) * parseInt(editCl) / 100)).toFixed(2)} €/l</>
            )}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={handleSave}
          disabled={!editUnits || !editCl}
          className="text-xs bg-blue-600 text-white px-2.5 py-1 rounded hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          OK
        </button>
        <button
          onClick={handleClear}
          className="text-xs text-stone-500 hover:text-stone-700 flex items-center gap-0.5"
        >
          <X size={11} />
          Annuler
        </button>

        {/* Quick presets for common Belgian formats */}
        <div className="flex gap-1 ml-auto">
          {[
            { label: '24×33', u: 24, cl: 33 },
            { label: '24×25', u: 24, cl: 25 },
            { label: '24×50', u: 24, cl: 50 },
            { label: '12×75', u: 12, cl: 75 },
          ].map((preset) => (
            <button
              key={preset.label}
              onClick={() => {
                setEditUnits(preset.u.toString());
                setEditCl(preset.cl.toString());
              }}
              className="text-[10px] text-blue-500 hover:text-blue-700 border border-blue-200 rounded px-1.5 py-0.5 hover:bg-blue-100"
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
