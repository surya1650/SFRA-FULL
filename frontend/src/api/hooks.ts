/**
 * TanStack Query hooks wrapping the typed API client.
 *
 * Cache keys live as constants so invalidation is centralised — when an
 * upload mutates a session's traces, we invalidate the matching query
 * key and TanStack re-fetches in the background.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type {
  AnalysisResult,
  InterventionType,
  SessionType,
  TraceData,
  TraceRole,
  Transformer,
  TransformerType,
} from "./client";

export const qk = {
  health: ["health"] as const,
  combinations: (t: TransformerType) => ["combinations", t] as const,
  bands: ["bands"] as const,
  transformers: ["transformers"] as const,
  transformer: (id: string) => ["transformer", id] as const,
  cycles: (id: string) => ["cycles", id] as const,
  cycleSessions: (id: string) => ["cycle", id, "sessions"] as const,
  transformerSessions: (id: string) => ["transformer", id, "sessions"] as const,
  session: (id: string) => ["session", id] as const,
  sessionAnalyses: (id: string) => ["session", id, "analyses"] as const,
  sessionTraces: (id: string) => ["session", id, "traces"] as const,
  trace: (id: string) => ["trace", id] as const,
  traceData: (id: string) => ["trace", id, "data"] as const,
};

// -------- Health -----------------------------------------------------------
export function useHealth() {
  return useQuery({
    queryKey: qk.health,
    queryFn: api.health,
    refetchInterval: 30_000,
  });
}

// -------- Standards --------------------------------------------------------
export function useCombinations(transformerType: TransformerType | null) {
  return useQuery({
    queryKey: transformerType
      ? qk.combinations(transformerType)
      : ["combinations", "_off"],
    queryFn: () => api.listCombinations(transformerType!),
    enabled: !!transformerType,
  });
}

export function useBands() {
  return useQuery({ queryKey: qk.bands, queryFn: api.getBands });
}

// -------- Transformers -----------------------------------------------------
export function useTransformers() {
  return useQuery({
    queryKey: qk.transformers,
    queryFn: api.listTransformers,
  });
}

export function useTransformer(id: string | null) {
  return useQuery({
    queryKey: id ? qk.transformer(id) : ["transformer", "_off"],
    queryFn: () => api.getTransformer(id!),
    enabled: !!id,
  });
}

export function useCreateTransformer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Parameters<typeof api.createTransformer>[0]) =>
      api.createTransformer(payload),
    onSuccess: (created: Transformer) => {
      qc.invalidateQueries({ queryKey: qk.transformers });
      qc.setQueryData(qk.transformer(created.id), created);
    },
  });
}

// -------- Cycles -----------------------------------------------------------
export function useCycles(transformerId: string | null) {
  return useQuery({
    queryKey: transformerId ? qk.cycles(transformerId) : ["cycles", "_off"],
    queryFn: () => api.listCycles(transformerId!),
    enabled: !!transformerId,
  });
}

export function useCreateCycle(transformerId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      intervention_type: InterventionType;
      cycle_start_date: string;
      remarks?: string;
    }) => api.createCycle(transformerId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.cycles(transformerId) }),
  });
}

// -------- Sessions ---------------------------------------------------------
export function useCreateSession(transformerId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      overhaul_cycle_id: string;
      session_type: SessionType;
      session_date: string;
      tested_by?: string;
      ambient_temp_c?: number;
      oil_temp_c?: number;
    }) => api.createSession(transformerId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.transformer(transformerId) }),
  });
}

export function useSession(id: string | null) {
  return useQuery({
    queryKey: id ? qk.session(id) : ["session", "_off"],
    queryFn: () => api.getSession(id!),
    enabled: !!id,
  });
}

export function useSessionAnalyses(id: string | null) {
  return useQuery({
    queryKey: id ? qk.sessionAnalyses(id) : ["sessionAnalyses", "_off"],
    queryFn: () => api.listSessionAnalyses(id!),
    enabled: !!id,
  });
}

// -------- Upload -----------------------------------------------------------
export function useUploadToSession(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      file,
      params,
    }: {
      file: File;
      params: Parameters<typeof api.uploadToSession>[2];
    }) => api.uploadToSession(sessionId, file, params),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.session(sessionId) });
      qc.invalidateQueries({ queryKey: qk.sessionAnalyses(sessionId) });
    },
  });
}

// -------- Analyse ----------------------------------------------------------
export function useAnalyseSession(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.analyseSession(sessionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.sessionAnalyses(sessionId) });
    },
  });
}

// -------- Trace data -------------------------------------------------------
export function useTraceData(id: string | null) {
  return useQuery({
    queryKey: id ? qk.traceData(id) : ["traceData", "_off"],
    queryFn: () => api.getTraceData(id!),
    enabled: !!id,
  });
}

// -------- Session / cycle browse ------------------------------------------
export function useTransformerSessions(id: string | null) {
  return useQuery({
    queryKey: id ? qk.transformerSessions(id) : ["transformerSessions", "_off"],
    queryFn: () => api.listSessionsForTransformer(id!),
    enabled: !!id,
  });
}

export function useCycleSessions(cycleId: string | null) {
  return useQuery({
    queryKey: cycleId ? qk.cycleSessions(cycleId) : ["cycleSessions", "_off"],
    queryFn: () => api.listSessionsForCycle(cycleId!),
    enabled: !!cycleId,
  });
}

export function useSessionTraces(sessionId: string | null) {
  return useQuery({
    queryKey: sessionId ? qk.sessionTraces(sessionId) : ["sessionTraces", "_off"],
    queryFn: () => api.listTracesForSession(sessionId!),
    enabled: !!sessionId,
  });
}

export type { AnalysisResult, TraceData, TraceRole };
