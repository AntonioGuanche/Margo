# Sprint 44 — Conditionnement éditable sur la review de facture

## Mise en contexte

Tu travailles sur **Margó**, un SaaS de gestion food cost pour restaurants belges. Stack : FastAPI (async) + React/TS/Tailwind, hébergé sur Railway, domaine heymargo.be. Sprint 43d complété (171 tests).

Commence par lire attentivement `CLAUDE.md` à la racine du projet pour comprendre l'architecture, les conventions et le contexte complet.

---

## Objectif

Quand un utilisateur review une facture, il doit pouvoir **voir et corriger le conditionnement** d'un produit AVANT de confirmer. L'objectif c'est que n'importe quel restaurateur puisse encoder la bonne info sans comprendre la logique technique derrière.

### Flux utilisateur cible

1. L'OCR lit "CHOUFFE BLONDE 24/3" → le backend détecte 24×33cl = 7.92L
2. La carte de la ligne affiche : **"📦 Casier : 24 × 33cl = 7.92L → sera stocké à 3.71 €/l"**
3. Si la détection est **fausse** ou **absente**, l'utilisateur clique un bouton et renseigne : nombre d'unités + cl par unité
4. Au confirm → le prix est automatiquement converti en €/l

---

## Ce qui existe déjà

- **Backend** (`unit_parser.py`) : `parse_packaging_volume()` détecte `24/3` → `{units: 24, cl_per_unit: 33, total_volume_liters: 7.92}`
- **Backend** (`invoices.py`) : `_compute_portion_fields()` retourne `volume_liters` quand un packaging est détecté
- **Frontend** (`InvoiceLineCard.tsx`) : bandeau ambre pour `units_per_package` (lignes ~112-131) + bandeau bleu pour `volume_liters` (lignes ~133-175)
- **Frontend** (`handleConfirm` dans `InvoiceReview.tsx`) : Sprint 39 convertit en €/l quand `volume_liters > 0`
- **Types** : `LineState` a déjà `units_per_package`, `volume_liters`, `suggested_serving_cl`

### Ce qui manque

1. Le bandeau ambre (units_per_package) et le bandeau bleu (volume_liters) sont **séparés** et **pas éditables**
2. Si la détection échoue, l'utilisateur n'a **aucun moyen** d'ajouter le conditionnement
3. `handleConfirm` utilise `volume_liters` mais le bandeau ambre ne met PAS à jour `volume_liters`

---

## Fix — Remplacer les deux bandeaux par un seul bloc éditable

### Changements dans `LineState` (`frontend/src/types/invoice.ts`)

Ajouter deux champs optionnels à `LineState` :

```typescript
export interface LineState {
  // ... existant ...
  // NEW: user-editable packaging override
  packaging_units: number | null;    // nombre d'unités dans le conditionnement
  packaging_cl_per_unit: number | null;  // cl par unité
}
```

### Initialisation dans `InvoiceReview.tsx`

Là où les `LineState` sont créés à partir des données du backend (le `setLines(...)` dans l'init), ajouter l'initialisation :

```typescript
packaging_units: null,      // sera rempli par le composant si détecté ou édité
packaging_cl_per_unit: null,
```

### Nouveau composant : `PackagingEditor.tsx`

Créer `frontend/src/components/PackagingEditor.tsx` :

```tsx
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
```

### Modifier `InvoiceLineCard.tsx`

**1. Importer le composant :**
```typescript
import PackagingEditor from './PackagingEditor';
```

**2. Supprimer les deux bandeaux existants** :
- Le bandeau ambre `units_per_package` (lignes ~112-131 : `{!line.is_manual && line.units_per_package != null ...}`)
- Le bandeau bleu `volume_liters` (lignes ~133-175 : `{!line.is_manual && line.volume_liters != null ...}`)

**3. Les remplacer par un seul `PackagingEditor`** :

Après le bloc d'affichage des prix (après la ligne `</div>` qui ferme le bloc quantity/unit_price/total_price, vers ligne ~110), ajouter :

```tsx
{/* Packaging editor — for all non-manual, non-ignored lines */}
{!line.is_manual && !line.ignored && (
  <PackagingEditor
    detectedUnits={line.units_per_package}
    detectedClPerUnit={
      // If volume_liters and units_per_package are both set, derive cl_per_unit
      line.volume_liters && line.units_per_package
        ? Math.round(line.volume_liters * 100 / line.units_per_package)
        : null
    }
    detectedVolumeLiters={line.volume_liters}
    packagingUnits={line.packaging_units}
    packagingClPerUnit={line.packaging_cl_per_unit}
    totalPrice={line.total_price}
    quantity={line.quantity}
    onChange={(updates) => onChange({
      packaging_units: updates.packaging_units,
      packaging_cl_per_unit: updates.packaging_cl_per_unit,
      volume_liters: updates.volume_liters,
    })}
  />
)}
```

### Modifier `handleConfirm` dans `InvoiceReview.tsx`

Le confirm doit utiliser `volume_liters` (qui est maintenant maintenu à jour par le PackagingEditor) pour convertir en €/l.

**Vérifier** que le `handleConfirm` actuel (post-Sprint 39) fait bien :

```typescript
// Volume-based conversion to €/l
if (l.volume_liters && l.volume_liters > 0 && totalPrice != null && quantity != null && quantity !== 0) {
  effectiveUnit = 'l';
  effectiveUnitPrice = Math.abs(totalPrice) / (Math.abs(quantity) * l.volume_liters);
}
```

Si ce bloc est déjà présent → **rien à changer** dans handleConfirm. Le PackagingEditor met à jour `volume_liters` dans le LineState → le confirm utilise ce volume.

Si ce bloc n'est PAS présent (la version locale est pre-Sprint 39), l'ajouter dans handleConfirm comme spécifié dans le Sprint 39.

---

## Pour les données existantes déjà corrompues

Après le déploiement de ce sprint, il faudra corriger les 11 ingrédients existants. Utilise l'endpoint admin `fix-package-price` du Sprint 43d. Voici le script à coller dans la console DevTools **une seule fois** :

```javascript
const token = 'Bearer <ton-token>';
const h = { 'Authorization': token };

const fixes = [
  // [id, units_in_package, volume_cl_per_unit]
  [3723, 24, 20],    // 7 Up → 24×20cl
  [3730, 24, 25],    // Agrum → 24×25cl (à vérifier)
  [3918, 1, null, 20],  // Bière blanche → fût 20L (special)
  [3716, 24, 25],    // Bière N.A. → 24×25cl (à vérifier)
  [3725, 24, 20],    // Cécémel → 24×20cl (à vérifier)
  [3692, 24, 33],    // Chimay Bleue → 24×33cl
  [3708, 24, 33],    // Chouffe Blonde → 24×33cl
  [3717, 28, 25],    // Eau péti. 25cL → 28×25cl (à vérifier)
  [3719, 18, 50],    // Eau péti. 50cL → 18×50cl
  [3718, 28, 25],    // Eau plate 25cL → 28×25cl (à vérifier)
  [3720, 18, 50],    // Eau plate 50cL → 18×50cl
];

for (const [id, units, cl] of fixes) {
  if (cl) {
    const url = `/admin/ingredients/${id}/fix-package-price?units_in_package=${units}&volume_cl_per_unit=${cl}`;
    const r = await fetch(url, { method: 'POST', headers: h });
    const d = await r.json();
    console.log(`${d.ingredient}: ${d.old_price} €/${d.old_unit} → ${d.new_price} €/${d.new_unit}`);
  }
}

// Bière blanche (fût 20L) — special case: divide price by 20
// Already stored as "fût", need to convert to €/l
const r2 = await fetch('/admin/ingredients/3918/fix-package-price?units_in_package=20&volume_cl_per_unit=100', { method: 'POST', headers: h });
const d2 = await r2.json();
console.log(`${d2.ingredient}: ${d2.old_price} → ${d2.new_price} €/${d2.new_unit}`);

// Then recalculate all
const rr = await fetch('/admin/recalculate-all-food-costs', { method: 'POST', headers: h });
console.log(await rr.json());
```

**IMPORTANT** : Avant de lancer ce script, vérifie et corrige les conditionnements marqués "à vérifier". Si tu n'es pas sûr d'un conditionnement, retire la ligne du script — le restaurateur pourra le corriger au prochain import grâce au nouveau PackagingEditor.

---

## Tests

1. **TypeScript** : `npx tsc --noEmit`
2. **Build** : `npm run build`
3. **Tests backend** : `pytest` (aucun changement backend dans ce sprint)
4. Test manuel :
   - Ouvrir une facture avec "CHOUFFE BLONDE 24/3" → le PackagingEditor affiche "24 × 33cl = 7.92L → 3.71 €/l"
   - Cliquer le crayon → modifier les valeurs → le preview €/l se met à jour
   - Ouvrir une facture avec un produit SANS conditionnement détecté → le lien "Ajouter un conditionnement" apparaît
   - Cliquer → renseigner 24 × 33cl → confirmer → l'ingrédient est stocké en €/l
   - Les presets (24×33, 24×25, etc.) remplissent les champs

---

## Vérifications finales

```bash
cd backend && pytest
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

---

## Commit, push, archive

```bash
git add -A
git commit -m "feat: editable packaging info on invoice review (auto-detect + manual override + presets)"
git push
git archive -o "/c/Users/Utilisateur/Desktop/margo.zip" HEAD
```

---

## Mettre à jour CLAUDE.md

Section "Current sprint" :

```
Sprint 44 complete — PackagingEditor composant sur la review de facture. Remplace les deux bandeaux séparés (ambre units_per_package + bleu volume) par un bloc unique éditable. Auto-rempli par parse_packaging_volume, l'utilisateur peut modifier ou ajouter manuellement le conditionnement (Nb × cl). Presets rapides (24×33, 24×25, 24×50, 12×75). Le volume_liters est mis à jour dans le LineState → handleConfirm convertit automatiquement en €/l. Fonctionne pour tout utilisateur lambda sans comprendre la logique technique.
```
