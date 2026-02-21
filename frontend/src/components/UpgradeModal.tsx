import { useNavigate } from 'react-router-dom';

interface UpgradeModalProps {
  show: boolean;
  onClose: () => void;
  message: string;
}

export default function UpgradeModal({ show, onClose, message }: UpgradeModalProps) {
  const navigate = useNavigate();

  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl max-w-sm w-full p-6 space-y-4">
        <div className="text-center">
          <div className="text-4xl mb-3">🔒</div>
          <h2 className="text-lg font-bold text-stone-900">Limite atteinte</h2>
          <p className="text-stone-600 text-sm mt-2">{message}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 border border-stone-300 text-stone-700 py-2.5 rounded-lg font-medium hover:bg-stone-50"
          >
            Fermer
          </button>
          <button
            onClick={() => {
              onClose();
              navigate('/pricing');
            }}
            className="flex-1 bg-orange-700 text-white py-2.5 rounded-lg font-medium hover:bg-orange-800"
          >
            Voir les plans
          </button>
        </div>
      </div>
    </div>
  );
}
