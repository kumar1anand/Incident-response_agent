import { useEffect, useMemo, useState } from "react";
import { api, type GraphNode, type GraphResponse } from "../api";

interface Positioned extends GraphNode {
  x: number;
  y: number;
}

const W = 900;
const H = 620;
const CX = W / 2;
const CY = H / 2;

const TYPE_COLOR: Record<string, string> = {
  category: "#a78bfa",
  service: "#4f8cff",
  incident: "#34d399",
};

export default function Graph() {
  const [data, setData] = useState<GraphResponse | null>(null);
  const [error, setError] = useState("");
  const [hover, setHover] = useState<string | null>(null);

  useEffect(() => {
    api
      .graph()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load graph."));
  }, []);

  const layout = useMemo(() => {
    if (!data) return { nodes: [] as Positioned[], pos: {} as Record<string, Positioned> };

    const categories = data.nodes.filter((n) => n.type === "category");
    const services = data.nodes.filter((n) => n.type === "service");
    const incidents = data.nodes.filter((n) => n.type === "incident");

    const pos: Record<string, Positioned> = {};

    // Categories: inner ring.
    categories.forEach((n, i) => {
      const a = (2 * Math.PI * i) / Math.max(categories.length, 1) - Math.PI / 2;
      pos[n.id] = { ...n, x: CX + Math.cos(a) * 150, y: CY + Math.sin(a) * 150 };
    });

    // Services: outer ring.
    services.forEach((n, i) => {
      const a = (2 * Math.PI * i) / Math.max(services.length, 1) - Math.PI / 2 + 0.3;
      pos[n.id] = { ...n, x: CX + Math.cos(a) * 270, y: CY + Math.sin(a) * 270 };
    });

    // Incidents: clustered near their category node.
    const perCat: Record<string, number> = {};
    incidents.forEach((n) => {
      const catId = `cat:${n.category}`;
      const anchor = pos[catId] ?? { x: CX, y: CY };
      const k = perCat[catId] ?? 0;
      perCat[catId] = k + 1;
      const a = (2 * Math.PI * k) / 6 + k * 0.5;
      const r = 46 + (k % 3) * 20;
      pos[n.id] = {
        ...n,
        x: anchor.x + Math.cos(a) * r,
        y: anchor.y + Math.sin(a) * r,
      };
    });

    return { nodes: Object.values(pos), pos };
  }, [data]);

  const connected = useMemo(() => {
    if (!hover || !data) return new Set<string>();
    const s = new Set<string>([hover]);
    data.edges.forEach((e) => {
      if (e.source === hover) s.add(e.target);
      if (e.target === hover) s.add(e.source);
    });
    return s;
  }, [hover, data]);

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">🕸️ Memory Graph</h1>
        <p className="page-desc">
          How IncidentIQ's knowledge connects: incidents link to the services
          they hit and the root-cause families they belong to. Hover a node to
          trace its relationships.
        </p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="graph-legend">
        <span><i style={{ background: TYPE_COLOR.category }} /> Root-cause family</span>
        <span><i style={{ background: TYPE_COLOR.service }} /> Service</span>
        <span><i style={{ background: TYPE_COLOR.incident }} /> Incident</span>
      </div>

      {!data ? (
        <div className="empty"><div className="big">🕸️</div>Building graph…</div>
      ) : (
        <div className="card graph-wrap">
          <svg viewBox={`0 0 ${W} ${H}`} className="graph-svg">
            {/* edges */}
            {data.edges.map((e, i) => {
              const a = layout.pos[e.source];
              const b = layout.pos[e.target];
              if (!a || !b) return null;
              const active = hover ? connected.has(e.source) && connected.has(e.target) : false;
              return (
                <line
                  key={i}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  className={`gedge ${active ? "active" : ""} ${hover && !active ? "dim" : ""}`}
                />
              );
            })}

            {/* nodes */}
            {layout.nodes.map((n) => {
              const r =
                n.type === "category" ? 22 : n.type === "service" ? 18 : 9;
              const faded = hover && !connected.has(n.id);
              return (
                <g
                  key={n.id}
                  transform={`translate(${n.x},${n.y})`}
                  className={`gnode ${faded ? "faded" : ""}`}
                  onMouseEnter={() => setHover(n.id)}
                  onMouseLeave={() => setHover(null)}
                >
                  <circle r={r} fill={TYPE_COLOR[n.type]} className="gnode-circle" />
                  {(n.type !== "incident" || hover === n.id) && (
                    <text
                      y={r + 13}
                      textAnchor="middle"
                      className={`gnode-label ${n.type}`}
                    >
                      {n.label}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          <NodeDetail node={hover ? layout.pos[hover] : null} />
        </div>
      )}
    </div>
  );
}

function NodeDetail({ node }: { node: Positioned | null | undefined }) {
  if (!node) {
    return (
      <div className="graph-detail muted">Hover a node to inspect it.</div>
    );
  }
  return (
    <div className="graph-detail">
      <div className="gd-type">{node.type}</div>
      <div className="gd-label">{node.label}</div>
      {node.type === "incident" && (
        <div className="gd-meta">
          <span>Service: {node.service}</span>
          <span>Severity: {node.severity}</span>
          <span>Category: {node.category}</span>
        </div>
      )}
      {node.type !== "incident" && (
        <div className="gd-meta">
          <span>Connected incidents: {node.weight}</span>
        </div>
      )}
    </div>
  );
}
