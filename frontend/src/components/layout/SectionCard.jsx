export default function SectionCard({ title, subtitle, actions, children, className = "" }) {
  return (
    <section className={`glass-card p-5 ${className}`.trim()}>
      {(title || subtitle || actions) ? (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            {title ? <h3 className="text-lg font-semibold">{title}</h3> : null}
            {subtitle ? <p className="mt-1 text-sm text-aegis-muted">{subtitle}</p> : null}
          </div>
          {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
        </div>
      ) : null}
      {children}
    </section>
  );
}
