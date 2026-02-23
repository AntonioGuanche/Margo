import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, Camera, Mail, Loader2, X, Check, AlertCircle } from 'lucide-react';
import { useUploadInvoice } from '../hooks/useInvoices';

type FileStatus = 'pending' | 'uploading' | 'done' | 'error';

interface QueuedFile {
  file: File;
  status: FileStatus;
  invoiceId?: number;
  error?: string;
}

export default function InvoiceUpload() {
  const navigate = useNavigate();
  const upload = useUploadInvoice();
  const [isDragging, setIsDragging] = useState(false);
  const [queue, setQueue] = useState<QueuedFile[]>([]);
  const processingRef = useRef(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processQueue = useCallback(
    async (currentQueue: QueuedFile[]) => {
      if (processingRef.current) return;
      processingRef.current = true;

      const updated = [...currentQueue];
      for (let i = 0; i < updated.length; i++) {
        if (updated[i].status !== 'pending') continue;

        // Mark as uploading
        updated[i] = { ...updated[i], status: 'uploading' };
        setQueue([...updated]);

        try {
          const result = await new Promise<{ invoice_id: number }>((resolve, reject) => {
            upload.mutate(updated[i].file, {
              onSuccess: (data) => resolve(data),
              onError: (err) => reject(err),
            });
          });
          updated[i] = { ...updated[i], status: 'done', invoiceId: result.invoice_id };
        } catch (err) {
          updated[i] = {
            ...updated[i],
            status: 'error',
            error: err instanceof Error ? err.message : 'Erreur inconnue',
          };
        }
        setQueue([...updated]);
      }

      processingRef.current = false;
    },
    [upload],
  );

  const addFiles = useCallback(
    (files: FileList) => {
      const newEntries: QueuedFile[] = Array.from(files).map((file) => ({
        file,
        status: 'pending' as FileStatus,
      }));
      setQueue((prev) => {
        const merged = [...prev, ...newEntries];
        // Auto-process
        setTimeout(() => processQueue(merged), 0);
        return merged;
      });
    },
    [processQueue],
  );

  const removeFile = useCallback((index: number) => {
    setQueue((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files);
      }
    },
    [addFiles],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        addFiles(e.target.files);
        e.target.value = ''; // Reset to allow re-selecting same file
      }
    },
    [addFiles],
  );

  // Count statuses
  const doneCount = queue.filter((q) => q.status === 'done').length;
  const isProcessing = queue.some((q) => q.status === 'uploading');

  return (
    <div>
      <h2 className="text-xl font-semibold text-stone-900 mb-4 flex items-center gap-2">
        <Upload size={22} className="text-orange-700" />
        Importer des factures
      </h2>

      {/* Drop zone — accepts multiple files */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        className={`
          border-2 border-dashed rounded-xl p-8 text-center transition-colors mb-4
          ${isDragging ? 'border-orange-500 bg-orange-50' : 'border-stone-300 bg-white'}
        `}
      >
        <FileText size={40} className="mx-auto text-stone-300 mb-3" />
        <p className="text-stone-600 font-medium mb-1">
          Glisse tes factures ici
        </p>
        <p className="text-sm text-stone-400 mb-4">
          XML, PDF, ou images — plusieurs fichiers possibles
        </p>

        <label className="inline-flex items-center gap-2 bg-orange-700 text-white px-6 py-3 rounded-xl font-medium hover:bg-orange-800 transition-colors cursor-pointer">
          <Upload size={18} />
          Choisir des fichiers
          <input
            ref={fileInputRef}
            type="file"
            accept=".xml,.pdf,.jpg,.jpeg,.png,.webp"
            multiple
            onChange={handleInputChange}
            className="hidden"
          />
        </label>
      </div>

      {/* File queue */}
      {queue.length > 0 && (
        <div className="space-y-2 mb-4">
          <h3 className="text-sm font-medium text-stone-500 uppercase tracking-wide">
            {queue.length} fichier{queue.length > 1 ? 's' : ''} — {doneCount} traité{doneCount > 1 ? 's' : ''}
          </h3>
          {queue.map((item, index) => (
            <div
              key={index}
              className="bg-white rounded-lg border border-stone-200 px-4 py-3 flex items-center gap-3"
            >
              {/* Status icon */}
              {item.status === 'pending' && (
                <div className="w-6 h-6 rounded-full bg-stone-100 flex items-center justify-center shrink-0">
                  <FileText size={14} className="text-stone-400" />
                </div>
              )}
              {item.status === 'uploading' && (
                <Loader2 size={18} className="text-orange-600 animate-spin shrink-0" />
              )}
              {item.status === 'done' && (
                <div className="w-6 h-6 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                  <Check size={14} className="text-emerald-600" />
                </div>
              )}
              {item.status === 'error' && (
                <div className="w-6 h-6 rounded-full bg-red-100 flex items-center justify-center shrink-0">
                  <AlertCircle size={14} className="text-red-600" />
                </div>
              )}

              {/* File info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-stone-900 truncate">{item.file.name}</p>
                {item.status === 'uploading' && (
                  <p className="text-xs text-stone-400">Analyse en cours...</p>
                )}
                {item.status === 'error' && (
                  <p className="text-xs text-red-600">{item.error}</p>
                )}
                {item.status === 'done' && (
                  <p className="text-xs text-emerald-600">Importée avec succès</p>
                )}
              </div>

              {/* Actions */}
              {item.status === 'done' && item.invoiceId && (
                <button
                  onClick={() => navigate(`/invoices/${item.invoiceId}/review`)}
                  className="text-xs text-orange-700 font-medium hover:text-orange-800"
                >
                  Vérifier
                </button>
              )}
              {(item.status === 'pending' || item.status === 'error') && (
                <button
                  onClick={() => removeFile(index)}
                  className="p-1 text-stone-400 hover:text-red-600 transition-colors"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          ))}

          {/* Review all button */}
          {doneCount > 0 && !isProcessing && (
            <button
              onClick={() => navigate('/invoices')}
              className="w-full bg-orange-700 text-white py-3 rounded-xl font-medium hover:bg-orange-800 transition-colors mt-2"
            >
              Voir mes factures ({doneCount} importée{doneCount > 1 ? 's' : ''})
            </button>
          )}
        </div>
      )}

      {/* Camera option */}
      <div className="bg-white rounded-xl border border-stone-200 p-4 mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center shrink-0">
            <Camera size={20} className="text-orange-700" />
          </div>
          <div className="flex-1">
            <p className="font-medium text-stone-900 text-sm">Scanner une facture</p>
            <p className="text-xs text-stone-500">Prendre en photo avec la caméra</p>
          </div>
          <label className="bg-stone-100 text-stone-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-stone-200 transition-colors cursor-pointer">
            Ouvrir
            <input
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleInputChange}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {/* Email forwarding info */}
      <div className="bg-white rounded-xl border border-stone-200 p-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center shrink-0">
            <Mail size={20} className="text-blue-700" />
          </div>
          <div className="flex-1">
            <p className="font-medium text-stone-900 text-sm">Transférer par email</p>
            <p className="text-xs text-stone-500 mt-0.5">
              Transfère tes factures fournisseurs à :
            </p>
            <p className="text-sm font-mono bg-stone-50 rounded-lg px-3 py-2 mt-2 text-orange-700 select-all">
              factures@heymargo.be
            </p>
            <p className="text-xs text-stone-400 mt-1">
              Les pièces jointes (PDF, XML, images) seront importées automatiquement.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
