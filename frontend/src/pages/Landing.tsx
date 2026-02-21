import { useNavigate } from 'react-router-dom';
import { Camera, FileText, BarChart3, Bell, Zap, ChefHat, ArrowRight, Mail } from 'lucide-react';

const features = [
  {
    icon: BarChart3,
    title: 'Dashboard food cost',
    desc: 'Visualise tes marges en temps réel, plat par plat.',
  },
  {
    icon: FileText,
    title: 'Import factures',
    desc: '3 canaux : email, upload, photo. Les prix se mettent à jour.',
  },
  {
    icon: Bell,
    title: 'Alertes automatiques',
    desc: 'Sois prévenu quand un ingrédient augmente et impacte tes marges.',
  },
  {
    icon: Zap,
    title: 'Simulateur "Et si"',
    desc: 'Simule un changement de prix ou de portion avant de décider.',
  },
  {
    icon: Camera,
    title: 'Onboarding AI',
    desc: 'Photographie ta carte, l\'AI extrait tes plats en 20 minutes.',
  },
];

const plans = [
  {
    name: 'Free',
    price: 'Gratuit',
    period: '',
    features: ['5 recettes', '3 factures/mois', 'Dashboard', 'Onboarding AI'],
    highlight: false,
  },
  {
    name: 'Pro',
    price: '14,90\u00a0\u20ac',
    period: '/mois',
    features: ['Recettes illimitées', 'Factures illimitées', 'Alertes email', 'Export CSV'],
    highlight: true,
  },
  {
    name: 'Multi',
    price: '24,90\u00a0\u20ac',
    period: '/mois',
    features: ["Tout Pro", "Jusqu'à 5 établissements", 'Dashboard consolidé'],
    highlight: false,
  },
];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-stone-50">
      {/* Nav */}
      <nav className="bg-white border-b border-stone-200 px-4 py-3 flex items-center justify-between max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold text-orange-700">Margó</h1>
        <button
          onClick={() => navigate('/login')}
          className="text-sm font-medium text-orange-700 hover:text-orange-800"
        >
          Se connecter
        </button>
      </nav>

      {/* Hero */}
      <section className="px-4 py-16 md:py-24 max-w-4xl mx-auto text-center">
        <h2 className="text-3xl md:text-5xl font-bold text-stone-900 leading-tight">
          Sais-tu vraiment ce que te coûte chaque plat ?
        </h2>
        <p className="mt-4 text-lg md:text-xl text-stone-600 max-w-2xl mx-auto">
          Margó calcule ton food cost en temps réel et t'alerte quand tes marges dérivent.
        </p>
        <button
          onClick={() => navigate('/login')}
          className="mt-8 inline-flex items-center gap-2 bg-orange-700 text-white px-6 py-3 rounded-lg font-medium text-lg hover:bg-orange-800 transition-colors"
        >
          Essayer gratuitement
          <ArrowRight size={20} />
        </button>
      </section>

      {/* Problème */}
      <section className="bg-white py-16 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <p className="text-2xl md:text-3xl font-semibold text-stone-800">
            60% des restaurants indépendants ne connaissent pas leur food cost réel.
          </p>
          <p className="mt-4 text-stone-600 text-lg">
            Un ingrédient qui augmente de 10% peut te coûter des centaines d'euros par mois sans que tu t'en rendes compte.
          </p>
        </div>
      </section>

      {/* Solution — 3 étapes */}
      <section className="py-16 px-4 max-w-5xl mx-auto">
        <h3 className="text-2xl font-bold text-center text-stone-900 mb-12">
          Comment ça marche
        </h3>
        <div className="grid md:grid-cols-3 gap-8">
          {[
            { emoji: '📸', title: 'Photographie ta carte', desc: "L'AI extrait tes plats en 20 min." },
            { emoji: '📥', title: 'Importe tes factures', desc: 'Les prix se mettent à jour tout seuls.' },
            { emoji: '📊', title: 'Visualise tes marges', desc: 'Dashboard + alertes + simulateur.' },
          ].map((step, i) => (
            <div key={i} className="text-center">
              <div className="text-5xl mb-4">{step.emoji}</div>
              <h4 className="text-lg font-semibold text-stone-900">{step.title}</h4>
              <p className="mt-2 text-stone-600">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Fonctionnalités */}
      <section className="bg-white py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <h3 className="text-2xl font-bold text-center text-stone-900 mb-12">
            Tout ce qu'il faut pour maîtriser tes marges
          </h3>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <div
                key={i}
                className="border border-stone-200 rounded-xl p-5"
              >
                <f.icon size={28} className="text-orange-700 mb-3" />
                <h4 className="font-semibold text-stone-900">{f.title}</h4>
                <p className="mt-1 text-sm text-stone-600">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-16 px-4" id="pricing">
        <div className="max-w-5xl mx-auto">
          <h3 className="text-2xl font-bold text-center text-stone-900 mb-12">
            Un plan pour chaque restaurant
          </h3>
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {plans.map((plan, i) => (
              <div
                key={i}
                className={`rounded-xl p-6 border-2 ${
                  plan.highlight
                    ? 'border-orange-700 bg-orange-50 shadow-lg relative'
                    : 'border-stone-200 bg-white'
                }`}
              >
                {plan.highlight && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-orange-700 text-white text-xs font-bold px-3 py-1 rounded-full">
                    Recommandé
                  </span>
                )}
                <h4 className="text-xl font-bold text-stone-900">{plan.name}</h4>
                <div className="mt-2">
                  <span className="text-3xl font-bold text-stone-900">{plan.price}</span>
                  <span className="text-stone-500">{plan.period}</span>
                </div>
                <ul className="mt-4 space-y-2">
                  {plan.features.map((f, j) => (
                    <li key={j} className="flex items-center gap-2 text-sm text-stone-700">
                      <span className="text-green-600">✓</span> {f}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => navigate('/login')}
                  className={`mt-6 w-full py-2.5 rounded-lg font-medium transition-colors ${
                    plan.highlight
                      ? 'bg-orange-700 text-white hover:bg-orange-800'
                      : 'border border-stone-300 text-stone-700 hover:bg-stone-50'
                  }`}
                >
                  Commencer
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA final */}
      <section className="bg-orange-700 py-16 px-4 text-center">
        <h3 className="text-2xl md:text-3xl font-bold text-white">
          Rejoins les restaurateurs qui maîtrisent leurs marges.
        </h3>
        <button
          onClick={() => navigate('/login')}
          className="mt-6 inline-flex items-center gap-2 bg-white text-orange-700 px-6 py-3 rounded-lg font-medium text-lg hover:bg-orange-50 transition-colors"
        >
          Commencer gratuitement
          <ArrowRight size={20} />
        </button>
      </section>

      {/* Footer */}
      <footer className="bg-stone-900 text-stone-400 py-8 px-4">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <ChefHat size={20} className="text-orange-500" />
            <span className="font-semibold text-white">Margó</span>
            <span className="text-sm">— heymargo.be</span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <a href="mailto:info@heymargo.be" className="flex items-center gap-1 hover:text-white">
              <Mail size={14} />
              info@heymargo.be
            </a>
            <span>Mentions légales</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
