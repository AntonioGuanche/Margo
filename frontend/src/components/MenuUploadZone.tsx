import { useState, useRef } from 'react';
import { Camera, Upload, FileText, Loader2, Pencil } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useExtractMenu } from '../hooks/useOnboarding';
import type { ExtractedDish } from '../hooks/useOnboarding';

interface MenuUploadZoneProps {
  onExtracted: (dishes: ExtractedDish[]) => void;
  /** Show the "Ajouter un plat manuellement" row */
  showManualAdd?: boolean;
}

export default function MenuUploadZone({ onExtracted, showManualAdd = true }: MenuUploadZoneProps) {
  const navigate = useNavigate();
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const extractMutation = useExtractMenu();
  const [extractionProgress, setExtractionProgress] = useState<{ current: number; total: number } | null>(null);

  async function handleMenuFiles(files: File[]) {
    if (files.length === 1) {
      extractMutation.mutate(files[0], {
        onSuccess: (data) => onExtracted(data.dishes),
      });
      return;
    }

    // Multi-file: extract each sequentially, merge results
    const allDishes: ExtractedDish[] = [];
    setExtractionProgress({ current: 0, total: files.length });

    for (let i = 0; i < files.length; i++) {
      setExtractionProgress({ current: i + 1, total: files.length });
      try {
        const data = await extractMutation.mutateAsync(files[i]);
        allDishes.push(...data.dishes);
      } catch (err) {
        console.error(`Error extracting file ${i + 1}:`, err);
        // Continue with other files
      }
    }

    setExtractionProgress(null);

    if (allDishes.length > 0) {
      onExtracted(allDishes);
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files).filter(f =>
      /\.(jpg|jpeg|png|webp|pdf)$/i.test(f.name)
    );
    if (files.length > 0) handleMenuFiles(files);
  };

  // Loading states
  if (extractionProgress) {
    return (
      <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
        <Loader2 size={40} className="text-orange-700 animate-spin mx-auto mb-3" />
        <p className="text-stone-600 font-medium">
          Extraction en cours... ({extractionProgress.current}/{extractionProgress.total})
        </p>
        <p className="text-sm text-stone-400 mt-1">
          Fichier {extractionProgress.current} sur {extractionProgress.total}
        </p>
      </div>
    );
  }

  if (extractMutation.isPending) {
    return (
      <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
        <Loader2 size={40} className="text-orange-700 animate-spin mx-auto mb-3" />
        <p className="text-stone-600 font-medium">Extraction des plats en cours...</p>
        <p className="text-sm text-stone-400 mt-1">L'IA analyse votre carte</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Drag & drop zone */}
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
        <p className="text-sm text-stone-400 mb-3">PDF ou image de ton menu (plusieurs fichiers possibles)</p>
        <div className="flex items-center justify-center gap-3">
          <label className="inline-flex items-center gap-2 bg-orange-700 text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-orange-800 cursor-pointer transition-colors">
            <Upload size={16} />
            Choisir un fichier
            <input
              ref={fileInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.webp,.pdf"
              multiple
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.length) handleMenuFiles(Array.from(e.target.files));
              }}
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
              onChange={(e) => {
                if (e.target.files?.[0]) handleMenuFiles([e.target.files[0]]);
              }}
            />
          </label>
        </div>
      </div>

      {showManualAdd && (
        <>
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
        </>
      )}

      {extractMutation.isError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {extractMutation.error.message}
        </div>
      )}
    </div>
  );
}
