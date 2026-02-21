import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, Camera, Mail, Loader2 } from 'lucide-react';
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

  // Loading state
  if (upload.isPending) {
    return (
      <div>
        <h2 className="text-xl font-semibold text-stone-900 mb-4 flex items-center gap-2">
          <Upload size={22} className="text-orange-700" />
          Importer une facture
        </h2>
        <div className="bg-white rounded-xl border border-stone-200 p-12 text-center">
          <Loader2 size={48} className="text-orange-700 animate-spin mx-auto mb-4" />
          <p className="text-stone-600 font-medium">Analyse de la facture en cours...</p>
          <p className="text-sm text-stone-400 mt-1">Extraction des lignes (quelques secondes)</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-stone-900 mb-4 flex items-center gap-2">
        <Upload size={22} className="text-orange-700" />
        Importer une facture
      </h2>

      {/* Option 1: Drop zone (files) */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`
          border-2 border-dashed rounded-xl p-8 text-center transition-colors mb-4
          ${isDragging ? 'border-orange-500 bg-orange-50' : 'border-stone-300 bg-white'}
        `}
      >
        <FileText size={40} className="mx-auto text-stone-300 mb-3" />
        <p className="text-stone-600 font-medium mb-1">
          Glisse ta facture ici
        </p>
        <p className="text-sm text-stone-400 mb-4">
          XML (UBL/Peppol), PDF, ou image
        </p>

        <label className="inline-flex items-center gap-2 bg-orange-700 text-white px-6 py-3 rounded-xl font-medium hover:bg-orange-800 transition-colors cursor-pointer">
          <Upload size={18} />
          Choisir un fichier
          <input
            type="file"
            accept=".xml,.pdf,.jpg,.jpeg,.png,.webp"
            onChange={handleInputChange}
            className="hidden"
          />
        </label>
      </div>

      {/* Option 2: Camera (photo) */}
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

      {/* Option 3: Email forwarding (info) */}
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
              factures@margo.be
            </p>
            <p className="text-xs text-stone-400 mt-1">
              Les pièces jointes (PDF, XML, images) seront importées automatiquement.
            </p>
          </div>
        </div>
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
