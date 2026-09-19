export default function HealthCard({ title, ok, pending = false, detail, children }) {
  return (
    <article className={`opsHealthCard ${pending ? "pending" : ok ? "healthy" : "unhealthy"}`}>
      <div className="opsHealthTitle">
        <span className="opsHealthDot" aria-hidden="true" />
        <strong>{title}</strong>
      </div>
      <span>{pending ? "Comprobando..." : ok ? "Disponible" : "Con problemas"}</span>
      {detail ? <small>{detail}</small> : null}
      {children}
    </article>
  );
}
