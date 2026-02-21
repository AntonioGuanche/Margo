import { Component, type ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error): void {
    console.error('ErrorBoundary caught:', error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
            <AlertTriangle size={32} className="text-red-600" />
          </div>
          <h2 className="text-lg font-semibold text-stone-900 mb-2">
            Oups, quelque chose a mal tourné
          </h2>
          <p className="text-sm text-stone-500 mb-6 max-w-xs">
            Une erreur inattendue s'est produite. Essaie de recharger la page.
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false });
              window.location.reload();
            }}
            className="bg-orange-700 text-white px-6 py-2.5 rounded-xl text-sm font-medium hover:bg-orange-800 transition-colors"
          >
            Recharger
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
