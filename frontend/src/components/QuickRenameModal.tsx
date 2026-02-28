import { useEffect, useRef, useState } from 'react';
import { Loader2 } from 'lucide-react';

interface QuickRenameModalProps {
  title: string;
  currentName: string;
  onSave: (newName: string) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export default function QuickRenameModal({
  title,
  currentName,
  onSave,
  onCancel,
  isLoading = false,
}: QuickRenameModalProps) {
  const [value, setValue] = useState(currentName);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.select();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && value.trim() && !isLoading) {
      onSave(value.trim());
    } else if (e.key === 'Escape') {
      onCancel();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 transition-opacity"
        onClick={onCancel}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-xl max-w-sm w-full p-6 animate-in fade-in zoom-in-95">
        <h3 className="text-base font-semibold text-stone-900 mb-4">{title}</h3>

        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          className="w-full border border-stone-300 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent mb-4 disabled:opacity-60"
        />

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1 bg-stone-100 text-stone-700 py-2.5 rounded-xl text-sm font-medium hover:bg-stone-200 transition-colors disabled:opacity-50"
          >
            Annuler
          </button>
          <button
            onClick={() => value.trim() && onSave(value.trim())}
            disabled={!value.trim() || isLoading}
            className="flex-1 bg-orange-600 text-white py-2.5 rounded-xl text-sm font-medium hover:bg-orange-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isLoading && <Loader2 size={14} className="animate-spin" />}
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  );
}
