/**
 * Typed API client for the APTRANSCO SFRA backend.
 *
 * All requests go through a single fetch wrapper so we can plug in auth
 * headers + error tracking later in one place. The JSON shapes mirror
 * the Pydantic schemas in src/sfra_full/api/schemas.py — keep them in
 * sync when the backend evolves.
 */

const API_BASE = "/api";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown, message?: string) {
    super(message || `API error ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "content-type": "application/json",
      ...(init.headers as Record<string, string> | undefined),
    },
    ...init,
  });
  const text = await res.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }
  if (!res.ok) {
    throw new ApiError(res.status, parsed);
  }
  return parsed as T;
}

// ---------------------------------------------------------------------------
// Types — mirror Pydantic v2 DTOs
// ---------------------------------------------------------------------------
export type TransformerType =
  | "TWO_WINDING"
  | "AUTO_WITH_TERTIARY_BROUGHT_OUT"
  | "AUTO_WITH_TERTIARY_BURIED"
  | "THREE_WINDING";

export type InterventionType =
  | "COMMISSIONING"
  | "MAJOR_OVERHAUL"
  | "ACTIVE_PART_INSPECTION"
  | "WINDING_REPLACEMENT"
  | "RELOCATION"
  | "OTHER";

export type SessionType =
  | "REFERENCE"
  | "ROUTINE"
  | "POST_FAULT"
  | "POST_OVERHAUL"
  | "COMMISSIONING";

export type TraceRole = "REFERENCE" | "TESTED";

export type Severity =
  | "NORMAL"
  | "MINOR_DEVIATION"
  | "SIGNIFICANT_DEVIATION"
  | "SEVERE_DEVIATION"
  | "APPEARS_NORMAL"
  | "SUSPECT"
  | "INDETERMINATE";

export type AnalysisMode = "comparative" | "reference_missing_analysis";

export interface Transformer {
  id: string;
  serial_no: string;
  transformer_type: TransformerType;
  nameplate_mva: number | null;
  hv_kv: number | null;
  lv_kv: number | null;
  tv_kv: number | null;
  vector_group: string | null;
  manufacturer: string | null;
  year_of_manufacture: number | null;
  substation: string | null;
  feeder_bay: string | null;
  has_oltc: boolean;
  oltc_make: string | null;
  oltc_steps_total: number | null;
  oltc_step_pct: number | null;
  has_detc: boolean;
  detc_steps_total: number | null;
  created_at: string;
  updated_at: string;
}

export interface OverhaulCycle {
  id: string;
  transformer_id: string;
  cycle_no: number;
  cycle_start_date: string;
  cycle_end_date: string | null;
  intervention_type: InterventionType;
  remarks: string | null;
  is_open: boolean;
}

export interface TestSession {
  id: string;
  transformer_id: string;
  overhaul_cycle_id: string;
  session_type: SessionType;
  session_date: string;
}

export interface Combination {
  id: number;
  transformer_type: TransformerType;
  code: string;
  sequence: number;
  category: string;
  winding: string;
  phase: string;
  injection_terminal: string;
  measurement_terminal: string;
  shorted_terminals: string[] | null;
  grounded_terminals: string[] | null;
  description: string | null;
}

export interface Trace {
  id: string;
  test_session_id: string;
  combination_id: number | null;
  role: TraceRole;
  label: string;
  tap_position_current: number | null;
  source_file_format: string;
  source_file_sha256: string | null;
  point_count: number;
  freq_min_hz: number;
  freq_max_hz: number;
  uploaded_at: string;
}

export interface TraceData {
  id: string;
  label: string;
  frequency_hz: number[];
  magnitude_db: number[];
  phase_deg: number[] | null;
  point_count: number;
  source_file_format: string;
  source_file_sha256: string | null;
}

export interface UnmappedSweep {
  sweep_index: number;
  label: string;
  suggested_code: string | null;
  reason: string;
}

export interface UploadResponse {
  detected_format: string;
  n_sweeps_parsed: number;
  n_traces_persisted: number;
  traces: Trace[];
  unmapped_sweeps: UnmappedSweep[];
}

export interface AnalysisResult {
  id: string;
  test_session_id: string;
  combination_id: number | null;
  tested_trace_id: string;
  reference_trace_id: string | null;
  mode: AnalysisMode;
  severity: Severity;
  indicators_json: Record<string, unknown> | null;
  resonances_json: Record<string, unknown>[] | null;
  poles_json: Record<string, unknown> | null;
  standalone_json: Record<string, unknown> | null;
  auto_remarks: string | null;
  engine_version: string;
  computed_at: string;
}

export interface RunAnalysisResponse {
  n_results: number;
  mode_1_count: number;
  mode_2_count: number;
  results: AnalysisResult[];
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------
export const api = {
  health: () => request<{ status: string; version: string }>("/health"),

  // Standards
  listCombinations: (transformer_type: TransformerType) =>
    request<Combination[]>(
      `/standards/combinations?transformer_type=${transformer_type}`,
    ),
  getBands: () =>
    request<{
      bands: Record<string, unknown>;
      dl_t_911_thresholds: Record<string, unknown>;
    }>("/standards/bands"),

  // Transformers
  listTransformers: () => request<Transformer[]>("/transformers"),
  createTransformer: (payload: Partial<Transformer> & { serial_no: string; transformer_type: TransformerType }) =>
    request<Transformer>("/transformers", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getTransformer: (id: string) => request<Transformer>(`/transformers/${id}`),

  // Cycles
  listCycles: (transformer_id: string) =>
    request<OverhaulCycle[]>(`/transformers/${transformer_id}/cycles`),
  createCycle: (
    transformer_id: string,
    payload: {
      intervention_type: InterventionType;
      cycle_start_date: string;
      remarks?: string;
    },
  ) =>
    request<OverhaulCycle>(`/transformers/${transformer_id}/cycles`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Sessions
  createSession: (
    transformer_id: string,
    payload: {
      overhaul_cycle_id: string;
      session_type: SessionType;
      session_date: string;
      tested_by?: string;
      ambient_temp_c?: number;
      oil_temp_c?: number;
    },
  ) =>
    request<TestSession>(`/transformers/${transformer_id}/sessions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getSession: (id: string) => request<TestSession>(`/sessions/${id}`),
  listSessionAnalyses: (id: string) =>
    request<AnalysisResult[]>(`/sessions/${id}/analyses`),

  // Upload — multipart, so don't go through the JSON helper
  uploadToSession: async (
    session_id: string,
    file: File,
    params: {
      role?: TraceRole;
      combination_code?: string;
      tap_position_current?: number;
      tap_position_previous?: number;
      tap_position_reference?: number;
      detc_tap_position?: number;
      notes?: string;
      uploaded_by?: string;
    } = {},
  ): Promise<UploadResponse> => {
    const fd = new FormData();
    fd.append("file", file);
    if (params.role) fd.append("role", params.role);
    if (params.combination_code)
      fd.append("combination_code", params.combination_code);
    if (params.tap_position_current != null)
      fd.append("tap_position_current", String(params.tap_position_current));
    if (params.tap_position_previous != null)
      fd.append("tap_position_previous", String(params.tap_position_previous));
    if (params.tap_position_reference != null)
      fd.append("tap_position_reference", String(params.tap_position_reference));
    if (params.detc_tap_position != null)
      fd.append("detc_tap_position", String(params.detc_tap_position));
    if (params.notes) fd.append("notes", params.notes);
    if (params.uploaded_by) fd.append("uploaded_by", params.uploaded_by);

    const res = await fetch(`${API_BASE}/sessions/${session_id}/upload`, {
      method: "POST",
      body: fd,
    });
    const text = await res.text();
    const body = text ? JSON.parse(text) : null;
    if (!res.ok) throw new ApiError(res.status, body);
    return body as UploadResponse;
  },

  analyseSession: (session_id: string) =>
    request<RunAnalysisResponse>(`/sessions/${session_id}/analyse`, {
      method: "POST",
    }),

  // Traces
  getTrace: (id: string) => request<Trace>(`/traces/${id}`),
  getTraceData: (id: string) => request<TraceData>(`/traces/${id}/data`),

  // Analyses
  getAnalysis: (id: string) => request<AnalysisResult>(`/analyses/${id}`),
};
