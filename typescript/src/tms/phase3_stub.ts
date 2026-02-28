/**
 * Phase 3 cross-language stub for ThoughtGraph/Reflection interoperability.
 * Python remains the reference implementation for Phase 3 in this repo.
 */

export type ReflectionMode =
  | "reasoning"
  | "summarization"
  | "contradiction_detection"
  | "planning";

export interface GraphStubStatus {
  status: "stub";
  language: "typescript";
  phase: 3;
  notes: string;
}

export function getPhase3StubStatus(): GraphStubStatus {
  return {
    status: "stub",
    language: "typescript",
    phase: 3,
    notes: "Implement ThoughtGraph + reflection runtime parity when TypeScript TMS backend is added.",
  };
}

