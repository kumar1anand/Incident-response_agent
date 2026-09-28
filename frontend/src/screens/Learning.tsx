import { useEffect, useState } from "react";
import { api, type LearningResponse, type MetricsResponse } from "../api";
import { LineChart, BarChart } from "../components/Charts";

export default function Learning() {
  const [data, setData] = useState<LearningResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.learning(), api.metrics()])
      .then(([l, m]) => {
        setData(l);
        setMetrics(m);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">📈 Agent Learning</h1>
        <p className="page-desc">
          How IncidentDeepDig improves as it accumulates memory. Each investigation
          draws on accumulated incident memories and both successful and failed remediation outcomes.
        </p>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {metrics && !metrics.available && (
        <div className="error-banner">{metrics.error || "Hindsight metrics are unavailable."}</div>
      )}

      {metrics && (metrics.available || metrics.learning_curve.length > 0) && (
        <div className="chart-grid2">
          <div className="card chart-card">
            <div className="section-label">Recall growth (per investigation)</div>
            <LineChart points={metrics.learning_curve} />
          </div>
          <div className="card chart-card">
            <div className="section-label">Remembered incidents by service</div>
            <BarChart data={metrics.by_service} />
          </div>
        </div>
      )}

      {metrics?.available && metrics.total_incidents > 0 && (
        <>
          <div className="section-label">Hindsight memory outcomes</div>
          <div className="stat-row">
            <div className="card stat">
              <div className="num">{metrics.total_incidents}</div>
              <div className="lbl">Incident experiences</div>
            </div>
            <div className="card stat">
              <div className="num">{metrics.outcomes.success}</div>
              <div className="lbl">Successful remediations</div>
            </div>
            <div className="card stat">
              <div className="num">{metrics.outcomes.failure}</div>
              <div className="lbl">Failed remediations</div>
            </div>
            <div className="card stat">
              <div className="num">{metrics.outcomes.unknown}</div>
              <div className="lbl">Outcome not recorded</div>
            </div>
          </div>
        </>
      )}

      {loading ? (
        <div className="empty">
          <div className="big">📈</div>
          Loading…
        </div>
      ) : !data || data.total_investigations === 0 ? (
        <div className="empty">
          <div className="big">🌱</div>
          No investigations yet. Run one on the Investigate screen (or Judge
          Mode) to grow the learning curve.
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
