import { useNavigate } from 'react-router-dom';
import { FileText, Plus, Clock, CheckCircle, Upload } from 'lucide-react';
import { useInvoices } from '../hooks/useInvoices';
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

function InvoiceRow({ invoice, onClick }: { invoice: InvoiceListItem; onClick: () => void }) {
  const date = invoice.invoice_date
    ? new Date(invoice.invoice_date).toLocaleDateString('fr-BE')
    : '—';

  return (
    <button
      onClick={onClick}
      className="w-full bg-white rounded-xl border border-stone-200 px-4 py-3 flex items-center justify-between hover:border-stone-300 transition-colors text-left"
    >
      <div className="min-w-0 flex-1">
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
      </div>
      <div className="flex items-center gap-3 ml-2 shrink-0">
        {invoice.total_amount != null && (
          <span className="text-sm font-semibold text-stone-700">
            {invoice.total_amount.toFixed(2)} €
          </span>
        )}
        <StatusBadge status={invoice.status} />
      </div>
    </button>
  );
}

export default function Invoices() {
  const navigate = useNavigate();
  const { data, isLoading } = useInvoices();

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-700" />
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

      {invoices.length === 0 ? (
        <div className="bg-white rounded-xl border border-stone-200 p-8 text-center">
          <Upload size={48} className="mx-auto text-stone-300 mb-4" />
          <p className="text-stone-500 mb-4">
            Aucune facture importée
          </p>
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
              onClick={() =>
                navigate(
                  invoice.status === 'pending_review'
                    ? `/invoices/${invoice.id}/review`
                    : `/invoices/${invoice.id}/review`,
                )
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
