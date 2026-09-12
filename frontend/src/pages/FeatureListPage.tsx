type Column = { key: string; label: string };

type FeatureListPageProps = {
  title: string;
  subtitle: string;
  columns: Column[];
  rows: Record<string, string>[];
};

export function FeatureListPage({ title, subtitle, columns, rows }: FeatureListPageProps) {
  return (
    <div>
      <header className="page-header">
        <div>
          <h1>{title}</h1>
          <p className="muted">{subtitle}</p>
        </div>
      </header>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key}>{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                {columns.map((c) => (
                  <td key={c.key}>{row[c.key] || "—"}</td>
                ))}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="muted">No records yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
