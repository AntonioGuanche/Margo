import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de l\'envoi');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-stone-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-orange-700">Margó</h1>
          <p className="text-stone-500 mt-2">
            Gestion des coûts alimentaires
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-stone-200 p-6">
          {sent ? (
            <div className="text-center">
              <div className="text-4xl mb-3">📧</div>
              <h2 className="text-lg font-semibold text-stone-900 mb-2">
                Vérifiez votre email
              </h2>
              <p className="text-stone-500 text-sm">
                Un lien de connexion a été envoyé à{' '}
                <span className="font-medium text-stone-700">{email}</span>
              </p>
              <button
                onClick={() => setSent(false)}
                className="mt-4 text-sm text-orange-700 hover:underline"
              >
                Utiliser un autre email
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="email"
                  className="block text-sm font-medium text-stone-700 mb-1"
                >
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full border border-stone-300 rounded-lg px-3 py-2.5 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
                  placeholder="antonio@restaurant.be"
                  required
                  autoFocus
                />
              </div>

              {error && (
                <p className="text-red-600 text-sm">{error}</p>
              )}

              <button
                type="submit"
                disabled={loading || !email}
                className="w-full bg-orange-700 text-white py-2.5 rounded-lg font-medium hover:bg-orange-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Envoi...' : 'Recevoir le lien de connexion'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
