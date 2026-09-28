import { useEffect, useState } from "react";
import { api, type PatternsResponse } from "../api";

export default function Patterns() {
  const [data, setData] = useState<PatternsResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .patterns()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load patterns."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">🔮 Pattern Insights</h1>
        <p className="page-desc">
          IncidentDeepDig doesn't just recall single incidents — it mines memory for
          recurring failure patterns and deployment risk, so you can prevent the
          next outage.
        </p>
      </div>

      {(error || (data && !data.available)) && (
        <div className="error-banner">{error || data?.error || "Hindsight insights are unavailable."}</div>
      )}

      {loading ? (
        <div className="empty"><div className="big">🔮</div>Analyzing memory…</div>
      ) : !data || !data.available ? (
        <div className="empty">Patterns need available Hindsight memory.</div>
      ) : data.total_incidents === 0 ? (
        <div className="empty">No incident experiences found in Hindsight memory yet.</div>
      ) : (
        <>
          {data.deployment_risk.warning && (
            <div className="card risk-banner">
              <div className="risk-icon">⚠️</div>
              <div>
                <div className="risk-title">Deployment risk detected</div>
                <div className="risk-text">{data.deployment_risk.warning}</div>
                <div className="risk-bar">
                  <div
                    className="risk-fill"
                    style={{ width: `${data.deployment_risk.share_pct}%` }}
                  />
                </div>
                <div className="risk-sub">
                  {data.deployment_risk.deploy_related} of {data.deployment_risk.total}{" "}
                  incidents followed a deployment
                </div>
              </div>
            </div>
          )}

          <div className="section-label">Recurring patterns ({data.patterns.length})</div>
          {data.patterns.length === 0 ? (
            <div className="empty">No repeated recorded categories found in Hindsight memory yet.</div>
          ) : <div className="grid">
            {data.patterns.map((p) => (
              <div className="card pattern-card" key={p.category}>
                <div className="pattern-head">
                  <span className="pattern-name">{p.category}</span>
                  <span className="pattern-count">{p.count}×</span>
                </div>

                <div className="pattern-stats">
                  <Stat label="Deploy-related" value={p.deploy_pct === null ? "—" : `${p.deploy_pct}%`} accent={p.deploy_pct !== null && p.deploy_pct >= 60} />
                  <Stat label="Avg duration" value={p.avg_duration_minutes === null ? "—" : `${p.avg_duration_minutes}m`} />
                  <Stat label="Services" value={String(p.services.length)} />
                  <Stat label="Worked / failed" value={`${p.successful_remediations} / ${p.failed_remediations}`} />
                </div>

                <div className="pattern-bar">
                  <div className="pattern-fill" style={{ width: `${p.deploy_pct}%` }} />
                </div>

                <div className="pattern-insight">{p.insight}</div>

                {p.services.length > 0 && (
                  <div className="pattern-services">
                    {p.services.map((s) => (
                      <span className="chip" key={s}>{s}</span>
                    ))}
                  </div>
                )}

                {p.common_resolutions.length > 0 && (
                  <div className="pattern-res">
                    <div className="lbl">Common resolutions</div>
                    <ul>
                      {p.common_resolutions.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {p.remediation_outcomes.length > 0 && (
                  <div className="pattern-res">
                    <div className="lbl">Remediation outcomes</div>
                    <ul>
                      {p.remediation_outcomes.map((r) => (
                        <li key={r.resolution}>
                          {r.resolution} — {r.success} success, {r.failure} failure
                          {r.unknown ? `, ${r.unknown} unknown` : ""}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>}
        </>
      )}
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="pstat">
      <div className={`pstat-val ${accent ? "accent" : ""}`}>{value}</div>
      <div className="pstat-lbl">{label}</div>
    </div>
  );
}
