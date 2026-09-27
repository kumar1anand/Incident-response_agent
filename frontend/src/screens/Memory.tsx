import { useEffect, useState } from "react";
import { api, type MemoryItem } from "../api";

export default function Memory() {
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .memory(100)
      .then((r) => {
        setItems(r.items);
        setTotal(r.total);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load memory."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">🧠 Incident Memory</h1>
        <p className="page-desc">
          Everything IncidentIQ has learned, stored in Hindsight. These memories
          power every investigation.
        </p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="match-line">
        <span className="match-count">{total}</span>
        memories remembered
      </div>

      {loading ? (
        <div className="empty">
          <div className="big">🧠</div>
          Loading memory…
        </div>
      ) : items.length === 0 ? (
        <div className="empty">
          <div className="big">🗂️</div>
          No memories yet. Seed incidents with <code>python -m app.load_incidents</code>.
        </div>
      ) : (
        <div className="grid">
          {items.map((m, i) => (
            <div className="card mem-card" key={m.id ?? i}>
              {m.fact_type && <span className="mem-tag">{m.fact_type}</span>}
              <div className="mem-text">{m.text}</div>
              <div className="mem-meta">
                {m.entities && <span>🏷️ {m.entities}</span>}
                {m.occurred_start && (
                  <span>📅 {formatDate(m.occurred_start)}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}
