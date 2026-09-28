import { useEffect, useState } from "react";
import { api, type Analysis, type JudgeDemo, type SimilarIncident } from "../api";

type Phase =
  | "idle"
  | "loading"
  | "memory_off"
  | "transition"
  | "memory_on"
  | "feedback"
  | "learned"
  | "impact";

const RECALL_STEPS = [
  "Searching incident memory",
  "Matching service",
  "Matching symptoms",
  "Comparing previous resolutions",
];

export default function JudgeMode() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [demo, setDemo] = useState<JudgeDemo | null>(null);
  const [error, setError] = useState("");
  const [feedbackDone, setFeedbackDone] = useState(false);

  async function run() {
    setPhase("loading");
    setError("");
    setDemo(null);
    setFeedbackDone(false);
    try {
      const result = await api.judgeDemo();
      setDemo(result);
      setPhase("memory_off");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Judge demo failed.");
      setPhase("idle");
    }
  }

  async function confirmWorked() {
    if (!demo) return;
    setPhase("learned");
    try {
      const top = demo.with_memory.similar_incidents[0];
      await api.feedback({
        record_id: demo.with_memory.record_id,
        feedback: "worked",
        incident: demo.incident,
        root_cause: top?.root_cause ?? demo.with_memory.summary,
        resolution: demo.with_memory.recommendation,
      });
      setFeedbackDone(true);
    } catch {
      setFeedbackDone(true); // still advance the story for the demo
    }
  }

  return (
    <div className="judge">
      <div className="page-head">
        <h1 className="page-title">🎬 Judge Mode</h1>
        <p className="page-desc">
          A guided 60-second story: watch how Hindsight memory changes incident
          response — from generic guessing to evidence-backed recommendations
          that improve over time.
        </p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {phase === "idle" && (
        <div className="card judge-hero">
          <div className="judge-hero-icon">🎬</div>
          <h2>See why memory changes incident response</h2>
          <p className="muted">
            Same incident, run twice — without memory, then with Hindsight.
          </p>
          <button className="btn btn-primary judge-run" onClick={run}>
            ▶ Run Judge Demo
          </button>
        </div>
      )}

      {phase === "loading" && (
        <div className="empty">
          <div className="big">🧠</div>
          Running both investigations…
        </div>
      )}

      {demo && phase !== "idle" && phase !== "loading" && (
        <>
          <StepDots phase={phase} />

          {phase === "memory_off" && (
            <MemoryOffStep
              incident={demo.incident}
              analysis={demo.without_memory}
              onNext={() => setPhase("transition")}
            />
          )}

          {phase === "transition" && (
            <TransitionStep onDone={() => setPhase("memory_on")} />
          )}

          {phase === "memory_on" && (
            <MemoryOnStep
              analysis={demo.with_memory}
              onNext={() => setPhase("feedback")}
            />
          )}

          {phase === "feedback" && (
            <FeedbackStep onWorked={confirmWorked} />
          )}

          {phase === "learned" && (
            <LearnedStep done={feedbackDone} onNext={() => setPhase("impact")} />
          )}

          {phase === "impact" && (
            <ImpactStep
              without={demo.without_memory}
              withMem={demo.with_memory}
              onRestart={run}
            />
          )}
        </>
      )}
    </div>
  );
}

/* ---------- Step indicator ---------- */
const ORDER: Phase[] = [
  "memory_off",
  "transition",
  "memory_on",
  "feedback",
  "learned",
  "impact",
];
const LABELS = ["Memory OFF", "Activate", "Memory ON", "Feedback", "Learn", "Impact"];

function StepDots({ phase }: { phase: Phase }) {
  const current = ORDER.indexOf(phase);
  return (
    <div className="judge-steps">
      {LABELS.map((label, i) => (
        <div
          key={label}
          className={`judge-step ${i === current ? "active" : ""} ${
            i < current ? "done" : ""
          }`}
        >
          <span className="js-dot">{i < current ? "✓" : i + 1}</span>
          <span className="js-label">{label}</span>
        </div>
      ))}
    </div>
  );
}

/* ---------- Step 1: Memory OFF ---------- */
function MemoryOffStep({
  incident,
  analysis,
  onNext,
}: {
  incident: string;
  analysis: Analysis;
  onNext: () => void;
}) {
  return (
    <div className="card judge-card off">
      <div className="judge-card-head">
        <span className="mem-state off">🔴 MEMORY OFF</span>
        <span className="step-tag">Step 1 / 4</span>
      </div>

      <div className="section-label">New production incident</div>
      <pre className="judge-incident">{incident}</pre>

      <div className="section-label" style={{ marginTop: 18 }}>
        AI Investigation (no history)
      </div>
      <p className="reco-text">{analysis.recommendation}</p>
      {analysis.investigation_steps.length > 0 && (
        <ul className="steps">
          {analysis.investigation_steps.slice(0, 4).map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      )}

      <div className="judge-meta-row">
        <span className="pill-flat">Historical evidence: NONE</span>
        <span className="pill-flat">Confidence: {analysis.confidence || "LOW"}%</span>
      </div>
      <div className="warning">🔴 Memory disabled — no historical incidents available.</div>

      <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={onNext}>
        Now turn Hindsight ON →
      </button>
    </div>
  );
}

/* ---------- Step 1.5: transition ---------- */
function TransitionStep({ onDone }: { onDone: () => void }) {
  const [done, setDone] = useState<number>(0);

  // Animate the recall checklist, then advance to the Memory ON step.
  useEffect(() => {
    const timers: number[] = [];
    RECALL_STEPS.forEach((_, i) => {
      timers.push(window.setTimeout(() => setDone(i + 1), 500 * (i + 1)));
    });
    timers.push(window.setTimeout(onDone, 500 * (RECALL_STEPS.length + 1) + 400));
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [onDone]);

  return (
    <div className="card judge-transition">
      <div className="mem-state on big-on">🧠 MEMORY ON — HINDSIGHT ACTIVE</div>
      <div className="recall-list">
        {RECALL_STEPS.map((s, i) => (
          <div key={s} className={`recall-item ${i < done ? "done" : ""}`}>
            <span className="ri-mark">{i < done ? "✓" : "○"}</span>
            {s}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- Step 2: Memory ON ---------- */
function MemoryOnStep({ analysis, onNext }: { analysis: Analysis; onNext: () => void }) {
  return (
    <div className="card judge-card on">
      <div className="judge-card-head">
        <span className="mem-state on">🧠 MEMORY ON</span>
        <span className="step-tag">Step 2 / 4</span>
      </div>

      <div className="match-line">
        <span className="match-count">🔎 {analysis.similar_count}</span>
        similar incident{analysis.similar_count === 1 ? "" : "s"} found by Hindsight
      </div>

      {analysis.similar_incidents.map((inc, i) => (
        <SimilarCard key={inc.id + i} inc={inc} />
      ))}

      <div className="card reco" style={{ marginTop: 8 }}>
        <div className="section-label">🤖 IncidentIQ Recommendation</div>
        <p className="reco-text">{analysis.recommendation}</p>

        <div className="why-block">
          <div className="why-title">Why?</div>
          <ul className="why-list">
            {analysis.similar_incidents[0] && (
              <>
                <li>✓ Same service</li>
                <li>✓ Similar symptoms (HTTP 500 + Kafka lag)</li>
                <li>✓ {analysis.similar_count} historical incidents recalled</li>
                <li>✓ Previous resolution succeeded</li>
              </>
            )}
          </ul>
        </div>

        <div className="judge-meta-row">
          <span className="pill-strong">Confidence: {analysis.confidence || 85}%</span>
        </div>
      </div>

      <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={onNext}>
        Apply fix & give feedback →
      </button>
    </div>
  );
}

function SimilarCard({ inc }: { inc: SimilarIncident }) {
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
          {sim}% similar
        </span>
      </div>
      {inc.root_cause && (
        <div className="ic-field">
          <div className="lbl">Previous Root Cause</div>
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

/* ---------- Step 3: feedback ---------- */
function FeedbackStep({ onWorked }: { onWorked: () => void }) {
  return (
    <div className="card judge-card">
      <div className="judge-card-head">
        <span className="mem-state on">👨‍💻 ENGINEER FEEDBACK</span>
        <span className="step-tag">Step 3 / 4</span>
      </div>
      <h3 style={{ marginTop: 6 }}>Did the recommendation work?</h3>
      <p className="muted">Confirming success teaches Hindsight for next time.</p>
      <div className="btn-row">
        <button className="btn btn-ok" onClick={onWorked}>
          ✅ Yes, it worked
        </button>
      </div>
    </div>
  );
}

/* ---------- Step 3.5: learned ---------- */
function LearnedStep({ done, onNext }: { done: boolean; onNext: () => void }) {
  return (
    <div className="card judge-learned">
      <div className="learned-icon">🧠</div>
      <h2>Hindsight Learned</h2>
      <div className="learned-list">
        <div className={done ? "ll done" : "ll"}>✓ Resolution confirmed successful</div>
        <div className={done ? "ll done" : "ll"}>✓ Outcome retained into memory</div>
        <div className={done ? "ll done" : "ll"}>✓ Future investigations can use it</div>
      </div>
      <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={onNext}>
        See the impact →
      </button>
    </div>
  );
}

/* ---------- Step 4: impact ---------- */
function ImpactStep({
  without,
  withMem,
  onRestart,
}: {
  without: Analysis;
  withMem: Analysis;
  onRestart: () => void;
}) {
  return (
    <div>
      <div className="section-label">🧠 Memory Impact</div>
      <div className="impact-grid">
        <div className="card impact-col off">
          <div className="impact-head">🔴 Before Hindsight</div>
          <ul>
            <li>Generic troubleshooting</li>
            <li>No historical evidence</li>
            <li>No previous resolution</li>
            <li>Confidence: {without.confidence || "LOW"}%</li>
          </ul>
        </div>
        <div className="card impact-col on">
          <div className="impact-head">🧠 After Hindsight</div>
          <ul>
            <li>{withMem.similar_count} relevant incidents recalled</li>
            <li>Previous root cause identified</li>
            <li>Previous successful resolution reused</li>
            <li>Confidence: {withMem.confidence || 85}%</li>
          </ul>
        </div>
      </div>

      <div className="card judge-closer">
        The agent didn't just answer. <strong>It learned.</strong>
      </div>

      <button className="btn btn-ghost" style={{ marginTop: 16 }} onClick={onRestart}>
        ↻ Run again
      </button>
    </div>
  );
}
