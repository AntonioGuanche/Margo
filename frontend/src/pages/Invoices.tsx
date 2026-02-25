import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Plus, Clock, CheckCircle, Upload, Trash2, Search } from 'lucide-react';
import { useInvoices, useDeleteInvoice } from '../hooks/useInvoices';
import { SkeletonList } from '../components/Skeleton';
import ConfirmModal from '../components/ConfirmModal';
import type { InvoiceListItem } from '../hooks/useInvoices';

function StatusBadge({ status }: { status: string }) {
  if (status === 'confirmed') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">
        <CheckCircle size={12} />
        Confirmée
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700">
      <Clock size={12} />
      En attente
    </span>
  );
}

function SourceBadge({ source }: { source: string }) {
  const labels: Record<string, string> = {
    upload: 'Upload',
    email: 'Email',
    photo: 'Photo',
  };
  return (
    <span className="text-xs px-1.5 py-0.5 rounded bg-stone-100 text-stone-600">
      {labels[source] ?? source}
    </span>
  );
}

function FormatBadge({ format }: { format: string }) {
  const colors: Record<string, string> = {
    xml: 'bg-blue-50 text-blue-700',
    pdf: 'bg-purple-50 text-purple-700',
    image: 'bg-stone-100 text-stone-600',
  };
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-medium uppercase ${colors[format] ?? colors.image}`}>
      {format}
    </span>
  );
}

function InvoiceRow({ invoice, onClick, onDelete }: { invoice: InvoiceListItem; onClick: () => void; onDelete: () => void }) {
  const date = invoice.invoice_date
    ? new Date(invoice.invoice_date).toLocaleDateString('fr-BE')
    : '—';

  return (
    <div className="w-full bg-white rounded-xl border border-stone-200 px-4 py-3 flex items-center justify-between group">
      <button
        onClick={onClick}
        className="min-w-0 flex-1 text-left hover:opacity-80 transition-opacity"
      >
        <div className="font-medium text-stone-900 truncate">
          {invoice.supplier_name ?? 'Fournisseur inconnu'}
        </div>
        <div className="text-sm text-stone-500 flex gap-2 mt-0.5 items-center">
          <span>{date}</span>
          <span>·</span>
          <span>{invoice.lines_count} ligne{invoice.lines_count > 1 ? 's' : ''}</span>
          <SourceBadge source={invoice.source} />
          <FormatBadge format={invoice.format} />
        </div>
      </button>
      <div className="flex items-center gap-3 ml-2 shrink-0">
        {invoice.total_amount != null && (
          <span className="text-sm font-semibold text-stone-700">
            {invoice.total_amount.toFixed(2)} €
          </span>
        )}
        <StatusBadge status={invoice.status} />
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="p-1.5 text-stone-300 hover:text-red-600 md:opacity-0 md:group-hover:opacity-100 transition-all"
          title="Supprimer"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}

export default function Invoices() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending_review' | 'confirmed'>('all');
  const { data, isLoading } = useInvoices(
    statusFilter === 'all' ? undefined : statusFilter,
    search || undefined,
  );
  const deleteMutation = useDeleteInvoice();
  const [deleting, setDeleting] = useState<InvoiceListItem | null>(null);

  if (isLoading) {
    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-stone-900 flex items-center gap-2">
            <FileText size={22} className="text-orange-700" />
            Factures
          </h2>
        </div>
        <SkeletonList count={4} />
      </div>
    );
  }

  const invoices = data?.items ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-stone-900 flex items-center gap-2">
          <FileText size={22} className="text-orange-700" />
          Factures
        </h2>
        <button
          onClick={() => navigate('/invoices/upload')}
          className="bg-orange-700 text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-orange-800 transition-colors flex items-center gap-1"
        >
          <Plus size={16} />
          Importer
        </button>
      </div>

      {/* Search + filter */}
      <div className="flex gap-2 mb-4">
        <div className="relative flex-1">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full border border-stone-300 rounded-lg pl-10 pr-3 py-2 text-stone-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
            placeholder="Rechercher un fournisseur..."
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as any)}
          className="border border-stone-300 rounded-lg px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none"
        >
          <option value="all">Toutes</option>
          <option value="pending_review">En attente</option>
          <option value="confirmed">Confirmées</option>
        </select>
      </div>

      {invoices.length === 0 ? (
        <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
          <Upload size={40} className="mx-auto text-stone-300 mb-3" />
          <p className="text-stone-600 font-medium mb-1">Aucune facture importée</p>
          <p className="text-sm text-stone-400 mb-4">Importe ta première facture.</p>
          <button
            onClick={() => navigate('/invoices/upload')}
            className="bg-orange-700 text-white px-6 py-3 rounded-xl font-medium hover:bg-orange-800 transition-colors"
          >
            Importer ma première facture
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {invoices.map((invoice) => (
            <InvoiceRow
              key={invoice.id}
              invoice={invoice}
              onClick={() => navigate(`/invoices/${invoice.id}/review`)}
              onDelete={() => setDeleting(invoice)}
            />
          ))}
        </div>
      )}

      {/* Modal suppression facture */}
      {deleting && (
        <ConfirmModal
          title={`Supprimer la facture ?`}
          message={`La facture de ${deleting.supplier_name ?? 'fournisseur inconnu'} sera supprimée. Cette action est irréversible.`}
          onConfirm={() => {
            deleteMutation.mutate(deleting.id, {
              onSuccess: () => setDeleting(null),
            });
          }}
          onCancel={() => setDeleting(null)}
          isLoading={deleteMutation.isPending}
        />
      )}
    </div>
  );
}
