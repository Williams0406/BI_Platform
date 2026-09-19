export default function Spinner({ label = "Loading…" }) {
  return (
    <div className="spinnerWrap" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
