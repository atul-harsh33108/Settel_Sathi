const architecturePrinciples = [
  "Evidence before explanation",
  "Deterministic money, bounded AI",
  "Approval before external action",
];

export default function App() {
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
        <strong>Synthetic demo data only.</strong> No live payment-provider or bank connection is
        enabled in this prototype.
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
