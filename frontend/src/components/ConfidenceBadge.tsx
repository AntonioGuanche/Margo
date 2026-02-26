export default function ConfidenceBadge({ confidence }: { confidence: string }) {
  const styles = {
    exact: 'bg-emerald-50 text-emerald-700',
    alias: 'bg-emerald-50 text-emerald-700',
    fuzzy: 'bg-amber-50 text-amber-700',
    none: 'bg-red-50 text-red-700',
    manual: 'bg-blue-50 text-blue-700',
  } as const;
  const labels = {
    exact: 'Exact',
    alias: 'Alias',
    fuzzy: 'Fuzzy',
    none: 'Aucun match',
    manual: 'Manuel',
  } as const;
  const style = styles[confidence as keyof typeof styles] ?? styles.none;
  const label = labels[confidence as keyof typeof labels] ?? 'Inconnu';

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style}`}>
      {label}
    </span>
  );
}
