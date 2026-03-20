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
  raw: Record<string, number>;
  normalized: Record<string, number>;
  review: Record<string, Record<string, number>>;
  compiled: Record<string, number>;
  dispatched: number;
  processed: number;
  index_age_seconds?: number;
  sources?: string[];
}

export interface NoteListItem {
  source_note_id: string;
  source: string;
  source_project?: string;
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
  user_keywords?: string[];
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
  note_type?: string[];
  note_count?: number;
  review_count?: number;
}

export interface TriageItem {
  source_note_id: string;
  source: string;
  source_project?: string;
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

export const getNote = async (
  id: string,
  source: string,
  sourceProject?: string,
): Promise<NoteDetail> => {
  const params = new URLSearchParams({ source });
  if (sourceProject) params.set('source_project', sourceProject);
  const res = await api<{ note: NoteDetail }>(`/api/notes/${id}?${params.toString()}`);
  return res.note;
};

export const getProjects = () => api<{ projects: Project[] }>('/api/projects');

export const getTriageItems = () => api<{ items: TriageItem[] }>('/api/triage');

export const getDecisions = () => api<{ decisions: unknown[] }>('/api/decisions');

export const suggestProject = (
  id: string,
  source: string,
  project: string,
  sourceProject?: string,
) =>
  api<{ ok: boolean }>(`/api/notes/${id}/suggest`, {
    method: 'POST',
    body: JSON.stringify({
      source,
      source_project: sourceProject,
      user_suggested_project: project,
    }),
  });

export const annotateNote = (
  id: string,
  source: string,
  reviewerNotes: string,
  userKeywords: string[],
  sourceProject?: string,
) =>
  api<{ ok: boolean }>(`/api/notes/${id}/annotate`, {
    method: 'POST',
    body: JSON.stringify({
      source,
      source_project: sourceProject,
      reviewer_notes: reviewerNotes,
      user_keywords: userKeywords,
    }),
  });

export const decideNote = (
  id: string,
  source: string,
  decision: string,
  finalProject?: string,
  sourceProject?: string,
) =>
  api<{ ok: boolean; decision: string; note_id: string }>(`/api/notes/${id}/decide`, {
    method: 'POST',
    body: JSON.stringify({
      source,
      source_project: sourceProject,
      decision,
      final_project: finalProject,
    }),
  });

export interface BatchDecideItem {
  note_id: string;
  source: string;
  source_project?: string;
  decision: string;
  final_project?: string;
}

export interface BatchDecideResult {
  note_id: string;
  ok: boolean;
  error?: string;
}

export const batchDecide = (items: BatchDecideItem[]) =>
  api<{ results: BatchDecideResult[] }>('/api/notes/batch-decide', {
    method: 'POST',
    body: JSON.stringify({ items }),
  });

export const refreshIndex = () => api<{ ok: boolean }>('/api/refresh', { method: 'POST' });

export const noteKey = (source: string, id: string, sourceProject?: string) =>
  `${source}::${sourceProject ?? ''}::${id}`;

export const noteIdentityParams = (note: {
  source_note_id: string;
  source: string;
  source_project?: string;
}) => {
  const params: Record<string, string> = {
    id: note.source_note_id,
    source: note.source,
  };
  if (note.source_project) params.source_project = note.source_project;
  return params;
};

export const noteHref = (note: {
  source_note_id: string;
  source: string;
  source_project?: string;
}) => `/notes?${new URLSearchParams(noteIdentityParams(note)).toString()}`;
