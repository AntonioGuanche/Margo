import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp } from 'lucide-react';
import { usePriceHistory } from '../hooks/useIngredients';

interface Props {
  ingredientId: number;
  onClose: () => void;
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('fr-BE', {
    day: '2-digit',
    month: 'short',
    year: '2-digit',
  });
}

export default function PriceHistoryChart({ ingredientId, onClose }: Props) {
  const { data, isLoading } = usePriceHistory(ingredientId);

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-stone-200 p-6">
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-orange-700" />
        </div>
      </div>
    );
  }

  if (!data) return null;

  const history = data.history;

  // Reverse to get chronological order for chart
  const chartData = [...history].reverse().map((entry) => ({
    date: formatDate(entry.date),
    prix: entry.price,
    rawDate: entry.date,
  }));

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-stone-900 flex items-center gap-2">
          <TrendingUp size={18} className="text-orange-700" />
          Historique — {data.ingredient_name}
        </h3>
        <button
          onClick={onClose}
          className="text-stone-400 hover:text-stone-600 text-sm"
        >
          Fermer
        </button>
      </div>

      {data.current_price != null && (
        <p className="text-sm text-stone-500 mb-3">
          Prix actuel : <span className="font-semibold text-stone-900">{data.current_price.toFixed(2)} €</span>
        </p>
      )}

      {history.length === 0 ? (
        <p className="text-sm text-stone-400 text-center py-4">
          Aucun historique de prix — confirmez une facture pour commencer.
        </p>
      ) : history.length < 2 ? (
        /* Less than 2 points → just show list */
        <div className="space-y-2">
          {history.map((entry, i) => (
            <div key={i} className="flex justify-between text-sm border-b border-stone-100 pb-2">
              <span className="text-stone-500">{formatDate(entry.date)}</span>
              <span className="font-medium text-stone-900">{entry.price.toFixed(2)} €</span>
              {entry.supplier_name && (
                <span className="text-stone-400 text-xs">{entry.supplier_name}</span>
              )}
            </div>
          ))}
        </div>
      ) : (
        /* 2+ points → show chart */
        <>
          <div className="h-48 -ml-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: '#78716c' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11, fill: '#78716c' }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v: number) => `${v}€`}
                />
                <Tooltip
                  formatter={(value: number | undefined) => [`${(value ?? 0).toFixed(2)} €`, 'Prix']}
                  contentStyle={{
                    borderRadius: '8px',
                    border: '1px solid #e7e5e4',
                    fontSize: '12px',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="prix"
                  stroke="#c2410c"
                  strokeWidth={2}
                  dot={{ fill: '#c2410c', r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* History list below chart */}
          <div className="mt-4 space-y-1.5 max-h-32 overflow-y-auto">
            {history.map((entry, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-stone-500">{formatDate(entry.date)}</span>
                <span className="font-medium text-stone-700">{entry.price.toFixed(2)} €</span>
                {entry.supplier_name && (
                  <span className="text-stone-400 truncate max-w-24">{entry.supplier_name}</span>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
