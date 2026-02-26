export const STATUS_COLORS = {
  green: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500', border: 'border-emerald-200' },
  orange: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500', border: 'border-amber-200' },
  red: { bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500', border: 'border-red-200' },
} as const;

export type MarginStatus = keyof typeof STATUS_COLORS;

export function StatusBadge({ status }: { status: MarginStatus }) {
  const colors = STATUS_COLORS[status];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
      {status === 'green' ? 'OK' : status === 'orange' ? 'Attention' : 'Critique'}
    </span>
  );
}
