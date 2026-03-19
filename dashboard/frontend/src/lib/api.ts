const BASE = '';

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export interface StatusResponse {
  raw: number;
  normalized: number;
  review: number;
  compiled: number;
  dispatched: number;
  processed: number;
  review_breakdown?: Record<string, number>;
  index_age_seconds?: number;
  sources?: string[];
}

export interface NoteListItem {
  source_note_id: string;
  source: string;
  title: string;
  status: string;
  project: string;
  user_suggested_project?: string;
  confidence: number;
  capture_kind: string;
  intent: string;
  destination: string;
  created_at: string;
  tags: string[];
  candidate_projects: Array<{ project: string; score: number }>;
  review_status?: string;
  reviewer_notes?: string;
  queue_age_seconds?: number;
  thread_id?: string;
  file_path?: string;
}

export interface NoteDetail extends NoteListItem {
  body: string;
  compiled?: Record<string, unknown>;
  decision?: Record<string, unknown>;
}

export interface NotesResponse {
  notes: NoteListItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface Project {
  key: string;
  display_name: string;
  language?: string;
  keywords?: string[];
  note_types?: string[];
  active_notes?: number;
  review_notes?: number;
  archived_notes?: number;
}

export interface TriageItem {
  source_note_id: string;
  source: string;
  title: string;
  status: string;
  project?: string;
  confidence: number;
  candidate_projects: Array<{ project: string; score: number }>;
  capture_kind?: string;
  category?: string;
  excerpt?: string;
  created_at?: string;
  user_suggested_project?: string;
}

export const getStatus = () => api<StatusResponse>('/api/status');

export const getNotes = (params?: Record<string, string>) => {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  return api<NotesResponse>(`/api/notes${qs}`);
};

export const getNote = (id: string, source: string) =>
  api<NoteDetail>(`/api/notes/${id}?source=${source}`);

export const getProjects = () => api<{ projects: Project[] }>('/api/projects');

export const getTriageItems = () => api<{ items: TriageItem[] }>('/api/triage');

export const getDecisions = () => api<{ decisions: unknown[] }>('/api/decisions');

export const suggestProject = (id: string, source: string, project: string) =>
  api<{ ok: boolean }>(`/api/notes/${id}/suggest`, {
    method: 'POST',
    body: JSON.stringify({ source, user_suggested_project: project }),
  });

export const annotateNote = (
  id: string,
  source: string,
  reviewerNotes: string,
  userKeywords: string[],
) =>
  api<{ ok: boolean }>(`/api/notes/${id}/annotate`, {
    method: 'POST',
    body: JSON.stringify({ source, reviewer_notes: reviewerNotes, user_keywords: userKeywords }),
  });

export const refreshIndex = () => api<{ ok: boolean }>('/api/refresh', { method: 'POST' });
