import { useEffect, useState } from "react";
import { api, type HistoryRecord } from "../api";

export default function History() {
  const [items, setItems] = useState<HistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .history()
      .then((r) => setItems(r.items))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load history."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">📋 Incident History</h1>
        <p className="page-desc">
          Every incident investigated by IncidentIQ, with the outcome the
          engineer reported.
        </p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="empty">
          <div className="big">📋</div>
          Loading…
        </div>
      ) : items.length === 0 ? (
        <div className="empty">
          <div className="big">📭</div>
          No investigations recorded yet.
        </div>
      ) : (
        items.map((rec) => (
          <div className="card hist-item" key={rec.id}>
            <div className="hist-body">
              {rec.summary && <div className="hist-summary">{rec.summary}</div>}
              <div className="hist-incident">{rec.incident}</div>
              <div className="mem-meta">
                <span>🔎 {rec.similar_count} similar recalled</span>
                <span>🕑 {formatDate(rec.created_at)}</span>
              </div>
            </div>
            {rec.feedback === "worked" ? (
              <span className="badge worked">✓ Resolved</span>
            ) : rec.feedback === "didnt_work" ? (
              <span className="badge didnt">✗ Didn't work</span>
            ) : (
              <span className="badge pending">Pending feedback</span>
            )}
          </div>
        ))
      )}
    </div>
  );
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}
