import { useEffect, useState } from "react";
import { api, type LearningResponse } from "../api";

export default function Learning() {
  const [data, setData] = useState<LearningResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .learning()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">📈 Agent Learning</h1>
        <p className="page-desc">
          How IncidentIQ improves as it accumulates memory. Each investigation
          draws on more recalled incidents and successful resolutions.
        </p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="empty">
          <div className="big">📈</div>
          Loading…
        </div>
      ) : !data || data.total_investigations === 0 ? (
        <div className="empty">
          <div className="big">🌱</div>
          No investigations yet. Run one on the Investigate screen to start the
          learning curve.
        </div>
      ) : (
        <>
          <div className="stat-row">
            <div className="card stat">
              <div className="num">{data.total_investigations}</div>
              <div className="lbl">Investigations</div>
            </div>
            <div className="card stat">
              <div className="num">{data.successful_resolutions}</div>
              <div className="lbl">Confirmed resolutions</div>
            </div>
            <div className="card stat">
              <div className="num">
                {data.milestones.length
                  ? Math.max(...data.milestones.map((m) => m.similar_count))
                  : 0}
              </div>
              <div className="lbl">Peak recalled incidents</div>
            </div>
          </div>

          <div className="section-label">Learning timeline</div>
          <div className="timeline">
            {data.milestones.map((m) => (
              <div
                key={m.index}
                className={`tl-item ${m.feedback === "worked" ? "worked" : ""}`}
              >
                <div className="card tl-card">
                  <div className="tl-index">Incident #{m.index}</div>
                  <div className="tl-summary">
                    {m.summary || describeStage(m.similar_count)}
                  </div>
                  <div className="tl-meta">
                    <span>🔎 {m.similar_count} recalled</span>
                    {m.feedback === "worked" && (
                      <span className="outcome-ok">✓ resolution confirmed</span>
                    )}
                    {m.feedback === "didnt_work" && <span>✗ did not work</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function describeStage(count: number) {
  if (count === 0) return "Generic troubleshooting — no prior memory to draw on";
  if (count < 3) return "Beginning to recall related incidents";
  return "Recognizing recurring patterns from memory";
}
