import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { verify } = useAuth();
  const [error, setError] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setError('Lien de connexion invalide');
      return;
    }

    verify(token)
      .then(() => navigate('/', { replace: true }))
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Erreur de vérification'),
      );
  }, [searchParams, verify, navigate]);

  if (error) {
    return (
      <div className="min-h-screen bg-stone-50 flex items-center justify-center px-4">
        <div className="text-center">
          <h2 className="text-lg font-semibold text-stone-900 mb-2">
            Erreur de connexion
          </h2>
          <p className="text-red-600 text-sm mb-4">{error}</p>
          <a href="/login" className="text-orange-700 hover:underline text-sm">
            Retour à la connexion
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-700 mx-auto mb-4" />
        <p className="text-stone-500">Connexion en cours...</p>
      </div>
    </div>
  );
}
