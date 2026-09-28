import { useState } from "react";
import { api, type Analysis, type SimilarIncident } from "../api";

const SAMPLE = `Payment Service returning HTTP 500 errors.
Kafka consumer lag increased to 12,500.
Started after deployment v2.4.1.`;

export default function Investigate() {
  const [incident, setIncident] = useState(SAMPLE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [feedbackSent, setFeedbackSent] = useState<"worked" | "didnt_work" | null>(null);
  const [memoryEnabled, setMemoryEnabled] = useState(true);

  async function investigate() {
    setLoading(true);
    setError("");
    setAnalysis(null);
    setFeedbackSent(null);
    try {
      const result = await api.investigate(incident, memoryEnabled);
      setAnalysis(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Investigation failed.");
    } finally {
      setLoading(false);
    }
  }

  async function sendFeedback(feedback: "worked" | "didnt_work") {
    if (!analysis) return;
    setFeedbackSent(feedback);
    try {
      const top = analysis.similar_incidents[0];
      await api.feedback({
        record_id: analysis.record_id,
        feedback,
        incident,
        root_cause: top?.root_cause ?? analysis.summary,
        resolution: analysis.recommendation,
      });
    } catch {
      setFeedbackSent(null);
      setError("Could not record feedback.");
    }
  }

  return (
    <div>
      <div className="page-head">
        <h1 className="page-title">🚨 Investigate</h1>
        <p className="page-desc">
          Describe the incident. IncidentDeepDig searches memory for similar past
          incidents and recommends next steps.
        </p>
      </div>

      <section className="section">
        <div className="section-label">New Incident</div>
        <textarea
          className="incident-input"
          value={incident}
          onChange={(e) => setIncident(e.target.value)}
          placeholder="Describe symptoms, affected service, recent changes…"
        />
        <div className="toolbar">
          <button
            className="btn btn-primary"
            onClick={investigate}
            disabled={loading || !incident.trim()}
          >
            {loading ? <span className="spinner" /> : "🔍"}
            {loading ? "Investigating…" : "Investigate"}
          </button>
          <button
            className="btn btn-ghost"
            onClick={() => setIncident(SAMPLE)}
            disabled={loading}
          >
            Reset sample
          </button>

          <div className="mem-toggle">
            <span className="mem-toggle-label">Hindsight Memory</span>
            <button
              className={`toggle ${memoryEnabled ? "on" : "off"}`}
              onClick={() => setMemoryEnabled((v) => !v)}
              disabled={loading}
              role="switch"
              aria-checked={memoryEnabled}
            >
              <span className="toggle-knob" />
              <span className="toggle-text">{memoryEnabled ? "ON" : "OFF"}</span>
            </button>
          </div>
        </div>
        <p className="mem-toggle-hint muted">
          {memoryEnabled
            ? "ON: the agent recalls and learns from historical incidents."
            : "OFF: the agent reasons only from the current incident."}
        </p>
      </section>

      {error && <div className="error-banner">{error}</div>}

      {analysis && (
        <section className="section">
          <div className="section-label">AI Investigation</div>

          <div className="match-line">
            <span className="match-count">🔎 {analysis.similar_count}</span>
            similar incident{analysis.similar_count === 1 ? "" : "s"} found in memory
          </div>

          {analysis.similar_incidents.map((inc, i) => (
            <IncidentCard key={inc.id + i} inc={inc} />
          ))}

          <div className="card reco section">
            <div className="section-label">AI Recommendation</div>
            <p className="reco-text">{analysis.recommendation}</p>

            {analysis.investigation_steps.length > 0 && (
              <ol className="steps">
                {analysis.investigation_steps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            )}

            {analysis.evidence_warning && (
              <div className="warning">⚠️ {analysis.evidence_warning}</div>
            )}

            <div className="btn-row">
              {feedbackSent === null ? (
                <>
                  <button className="btn btn-ok" onClick={() => sendFeedback("worked")}>
                    ✓ This Worked
                  </button>
                  <button
                    className="btn btn-bad"
                    onClick={() => sendFeedback("didnt_work")}
                  >
                    ✗ Didn't Work
                  </button>
                </>
              ) : feedbackSent === "worked" ? (
                <span className="badge worked">
                  ✓ Recorded — outcome retained into memory
                </span>
              ) : (
                <span className="badge didnt">✗ Recorded as unsuccessful</span>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

function IncidentCard({ inc }: { inc: SimilarIncident }) {
  const sim = Math.max(0, Math.min(100, Math.round(inc.similarity || 0)));
  return (
    <div className="card incident-card">
      <div className="ic-head">
        <div>
          <span className="ic-id">{inc.id}</span>
          {inc.service && <span className="ic-service">{inc.service}</span>}
        </div>
        <span className="similarity">
          <span className="sim-bar">
            <span className="sim-fill" style={{ width: `${sim}%` }} />
          </span>
          {sim}%
        </span>
      </div>

      {inc.root_cause && (
        <div className="ic-field">
          <div className="lbl">Root Cause</div>
          <div className="val">{inc.root_cause}</div>
        </div>
      )}
      {inc.resolution && (
        <div className="ic-field">
          <div className="lbl">Previous Resolution</div>
          <div className="val">{inc.resolution}</div>
        </div>
      )}
      {inc.outcome && (
        <div className="ic-field">
          <div className="lbl">Outcome</div>
          <div className="val outcome-ok">✅ {inc.outcome}</div>
        </div>
      )}
    </div>
  );
}
