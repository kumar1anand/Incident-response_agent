import { type CurvePoint } from "../api";

/** SVG line chart of recalled incidents over successive investigations. */
export function LineChart({ points }: { points: CurvePoint[] }) {
  const W = 640;
  const H = 240;
  const pad = 34;

  if (points.length === 0) {
    return <div className="muted">No investigations recorded yet.</div>;
  }

  const maxY = Math.max(3, ...points.map((p) => p.similar_count));
  const n = points.length;
  const x = (i: number) => pad + (i * (W - 2 * pad)) / Math.max(n - 1, 1);
  const y = (v: number) => H - pad - (v * (H - 2 * pad)) / maxY;

  const path = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(p.similar_count)}`)
    .join(" ");

  const area = `${path} L ${x(n - 1)} ${H - pad} L ${x(0)} ${H - pad} Z`;

  const gridLines = Array.from({ length: 4 }, (_, i) => (i * maxY) / 3);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg">
      <defs>
        <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#4f8cff" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#4f8cff" stopOpacity="0" />
        </linearGradient>
      </defs>

      {gridLines.map((g, i) => (
        <g key={i}>
          <line x1={pad} y1={y(g)} x2={W - pad} y2={y(g)} className="chart-grid" />
          <text x={pad - 8} y={y(g) + 4} textAnchor="end" className="chart-axis">
            {Math.round(g)}
          </text>
        </g>
      ))}

      <path d={area} fill="url(#area)" />
      <path d={path} className="chart-line" />

      {points.map((p, i) => (
        <circle
          key={i}
          cx={x(i)}
          cy={y(p.similar_count)}
          r={4}
          className={`chart-dot ${p.feedback === "worked" ? "worked" : ""}`}
        >
          <title>
            Investigation #{p.index}: {p.similar_count} recalled
            {p.feedback ? ` (${p.feedback})` : ""}
          </title>
        </circle>
      ))}

      <text x={W / 2} y={H - 6} textAnchor="middle" className="chart-axis">
        Investigations over time →
      </text>
    </svg>
  );
}

/** Horizontal bar chart from a label -> count map. */
export function BarChart({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) return <div className="muted">No data.</div>;
  const max = Math.max(...entries.map(([, v]) => v));

  return (
    <div className="barchart">
      {entries.map(([label, value]) => (
        <div className="barrow" key={label}>
          <span className="barlabel">{label}</span>
          <span className="bartrack">
            <span className="barfill" style={{ width: `${(100 * value) / max}%` }} />
          </span>
          <span className="barval">{value}</span>
        </div>
      ))}
    </div>
  );
}
