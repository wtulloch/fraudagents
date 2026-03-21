import { Database } from 'lucide-react';
import SyntheticDataGenerator from '../components/SyntheticData/SyntheticDataGenerator';

export default function SyntheticDataPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Database size={22} className="text-blue-500" /> Synthetic Data Studio
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Generate realistic fraud &amp; AML test data. Optionally index into Azure AI Search for RAG-powered agent testing.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <SyntheticDataGenerator />
        </div>

        {/* Info panel */}
        <div className="space-y-4">
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">What gets generated?</h3>
            <ul className="space-y-2 text-xs text-gray-300">
              {[
                ['Customers', 'Realistic PII with risk profiles, PEP flags'],
                ['Accounts', 'Bank accounts with jurisdiction & product type'],
                ['Transactions', 'Structured patterns (structuring, layering, card fraud)'],
                ['KYC Records', 'ID documents, source of funds, risk ratings'],
                ['Adverse Media', 'News articles linking entities to fraud'],
                ['Sanctions Entries', 'OFAC/EU/UN list records'],
              ].map(([title, desc]) => (
                <li key={title} className="flex items-start gap-2">
                  <span className="text-blue-500 mt-0.5">▸</span>
                  <div>
                    <p className="font-medium">{title}</p>
                    <p className="text-gray-500">{desc}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="card">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">AI Search Indexes</h3>
            <ul className="space-y-1.5 text-xs text-gray-300">
              {[
                ['transactions-index', 'Transaction + customer records'],
                ['kyc-index', 'KYC/KYB data + documents'],
                ['media-index', 'Adverse media corpus'],
                ['sanctions-index', 'OFAC / EU / UN / HMT lists'],
              ].map(([idx, desc]) => (
                <li key={idx} className="flex items-start gap-2">
                  <code className="text-blue-400 bg-blue-500/20 px-1.5 rounded shrink-0">{idx}</code>
                  <span className="text-gray-500">{desc}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card bg-amber-900/20 border-amber-800/50">
            <p className="text-xs text-amber-300">
              <span className="font-semibold">Tip:</span> Enable "Index to Azure AI Search" to let
              specialist agents retrieve context via RAG during investigation. This greatly improves
              finding quality and groundedness scores.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
