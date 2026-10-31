import { useEffect, useState } from "react";

const architecturePrinciples = [
  "Evidence before explanation",
  "Deterministic money, bounded AI",
  "Approval before external action",
];

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchInitialSummary() {
      try {
        const response = await fetch(`${API_BASE}/api/v1/imports/summary`);
        if (response.ok) {
          const data = await response.json();
          if (data.record_counts && Object.values(data.record_counts).some((v) => v > 0)) {
            setStatus({
              fixture_dir: "Database (current active state)",
              record_counts: data.record_counts,
            });
          }
        }
      } catch {
        // API might not be running yet; keep initial empty state
      }
    }
    fetchInitialSummary();
  }, []);

  async function handleLoadFixtures() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/api/v1/imports/seed`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error(`Import failed with status ${response.status}`);
      }
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load fixtures");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="hero" aria-labelledby="product-title">
        <p className="eyebrow">SETTLESAATHI · RELEASE 0</p>
        <h1 id="product-title">From collected payments to verified settlement.</h1>
        <p className="summary">
          The merchant financial-operations teammate for evidence-backed reconciliation and
          resolution workflows.
        </p>
      </section>

      <section className="notice" aria-label="Prototype data notice">
        <strong>Synthetic demo data only.</strong> Dataset: <code>v1 (Schema 1.0)</code> ·
        Organization: <code>Aarav Stores Demo Pvt. Ltd.</code> · Provider: <code>Paytm Mock</code>
      </section>

      <section className="import-card" aria-label="Synthetic data ingestion">
        <div className="import-header">
          <div>
            <h2>Data Ingestion & Provenance</h2>
            <p className="import-subtext">
              Certified synthetic fixtures with SHA-256 integrity verification and idempotent persistence.
            </p>
          </div>
          <button
            type="button"
            className="import-button"
            onClick={handleLoadFixtures}
            disabled={loading}
          >
            {loading ? "Importing..." : "Load Certified v1 Fixtures"}
          </button>
        </div>

        {error && <div className="import-error" role="alert">{error}</div>}

        {status && (
          <div className="import-results" aria-live="polite">
            <p className="import-success">
              ✓ Successfully verified & imported {status.fixture_dir}
            </p>
            <div className="counts-grid">
              <div className="count-item">
                <span className="count-num">{status.record_counts.transactions}</span>
                <span className="count-label">Transactions</span>
              </div>
              <div className="count-item">
                <span className="count-num">{status.record_counts.settlements}</span>
                <span className="count-label">Settlements</span>
              </div>
              <div className="count-item">
                <span className="count-num">{status.record_counts.settlement_line_items}</span>
                <span className="count-label">Line Items</span>
              </div>
              <div className="count-item">
                <span className="count-num">{status.record_counts.bank_entries}</span>
                <span className="count-label">Bank Entries</span>
              </div>
              <div className="count-item">
                <span className="count-num">{status.record_counts.mock_support_updates}</span>
                <span className="count-label">Support Updates</span>
              </div>
            </div>
          </div>
        )}
      </section>

      <section className="principles" aria-label="Product principles">
        {architecturePrinciples.map((principle) => (
          <article key={principle}>
            <span aria-hidden="true">✓</span>
            <p>{principle}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
