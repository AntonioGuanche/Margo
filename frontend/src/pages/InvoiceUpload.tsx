import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, Camera, Loader2 } from 'lucide-react';
import { useUploadInvoice } from '../hooks/useInvoices';

export default function InvoiceUpload() {
  const navigate = useNavigate();
  const upload = useUploadInvoice();
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = useCallback(
    (file: File) => {
      upload.mutate(file, {
        onSuccess: (data) => {
          navigate(`/invoices/${data.invoice_id}/review`);
        },
      });
    },
    [upload, navigate],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  return (
    <div>
      <h2 className="text-xl font-semibold text-stone-900 mb-4 flex items-center gap-2">
        <Upload size={22} className="text-orange-700" />
        Importer une facture
      </h2>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`
          border-2 border-dashed rounded-xl p-12 text-center transition-colors
          ${isDragging ? 'border-orange-500 bg-orange-50' : 'border-stone-300 bg-white'}
          ${upload.isPending ? 'opacity-50 pointer-events-none' : ''}
        `}
      >
        {upload.isPending ? (
          <div className="flex flex-col items-center gap-3">
            <Loader2 size={48} className="text-orange-700 animate-spin" />
            <p className="text-stone-600 font-medium">Analyse en cours...</p>
            <p className="text-sm text-stone-400">Extraction des lignes de facture</p>
          </div>
        ) : (
          <>
            <FileText size={48} className="mx-auto text-stone-300 mb-4" />
            <p className="text-stone-600 font-medium mb-2">
              Glisse ta facture ici (PDF ou XML)
            </p>
            <p className="text-sm text-stone-400 mb-6">
              Formats acceptés : XML (UBL/Peppol), PDF
            </p>

            <label className="inline-flex items-center gap-2 bg-orange-700 text-white px-6 py-3 rounded-xl font-medium hover:bg-orange-800 transition-colors cursor-pointer">
              <Upload size={18} />
              Choisir un fichier
              <input
                type="file"
                accept=".xml,.pdf,.jpg,.jpeg,.png"
                onChange={handleInputChange}
                className="hidden"
              />
            </label>

            <div className="mt-4">
              <button
                disabled
                className="inline-flex items-center gap-2 text-sm text-stone-400 cursor-not-allowed"
              >
                <Camera size={16} />
                Prendre en photo — Bientôt disponible
              </button>
            </div>
          </>
        )}
      </div>

      {/* Error */}
      {upload.isError && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {upload.error.message}
        </div>
      )}
    </div>
  );
}
