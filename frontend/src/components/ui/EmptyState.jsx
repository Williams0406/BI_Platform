import Link from "next/link";

export default function EmptyState({
  title,
  description,
  actionHref = "",
  actionLabel = "",
  secondaryHref = "",
  secondaryLabel = "",
}) {
  return (
    <div className="emptyState">
      <div className="emptyStateIcon">○</div>
      <h3>{title}</h3>
      <p>{description}</p>
      {actionHref && actionLabel ? (
        <div className="emptyStateActions">
          <Link className="button primaryButton" href={actionHref}>{actionLabel}</Link>
          {secondaryHref && secondaryLabel ? <Link className="button secondaryButton" href={secondaryHref}>{secondaryLabel}</Link> : null}
        </div>
      ) : null}
    </div>
  );
}
