// API client for the IncidentIQ backend.
// In dev, Vite proxies /api -> http://127.0.0.1:8000 (see vite.config.ts).

export interface SimilarIncident {
  id: string;
  similarity: number;
  service: string;
  root_cause: string;
  resolution: string;
  outcome: string;
}

export interface Analysis {
  similar_incidents: SimilarIncident[];
  similar_count: number;
  recommendation: string;
  investigation_steps: string[];
  evidence_warning: string;
  summary: string;
  confidence: number;
  raw_memories: string[];
  memory_enabled: boolean;
  record_id: number;
}

export interface JudgeDemo {
  incident: string;
  without_memory: Analysis;
  with_memory: Analysis;
}

export interface MemoryItem {
  id: string | null;
  text: string;
  context: string;
  entities: string;
  fact_type: string;
  occurred_start: string | null;
  updated_at: string | null;
}

export interface MemoryResponse {
  total: number;
  items: MemoryItem[];
}

export interface HistoryRecord {
  id: number;
  created_at: string;
  incident: string;
  summary: string;
  similar_count: number;
  recommendation: string;
  feedback: "worked" | "didnt_work" | null;
}

export interface HistoryResponse {
  total: number;
  items: HistoryRecord[];
}

export interface LearningMilestone {
  index: number;
  similar_count: number;
  summary: string;
  feedback: "worked" | "didnt_work" | null;
  created_at: string | null;
}

export interface LearningResponse {
  total_investigations: number;
  successful_resolutions: number;
  milestones: LearningMilestone[];
}

export interface Health {
  status: string;
  hindsight: boolean;
  bank_id: string;
}

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<Health>("/api/health"),

  investigate: (incident: string, memoryEnabled = true) =>
    req<Analysis>("/api/investigate", {
      method: "POST",
      body: JSON.stringify({ incident, memory_enabled: memoryEnabled }),
    }),

  judgeDemo: () =>
    req<JudgeDemo>("/api/judge-demo", { method: "POST" }),

  feedback: (payload: {
    record_id: number;
    feedback: "worked" | "didnt_work";
    incident?: string;
    root_cause?: string;
    resolution?: string;
  }) =>
    req<HistoryRecord>("/api/feedback", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  memory: (limit = 50) => req<MemoryResponse>(`/api/memory?limit=${limit}`),

  history: () => req<HistoryResponse>("/api/history"),

  learning: () => req<LearningResponse>("/api/learning"),
};
