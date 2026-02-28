import { describe, expect, it } from "vitest";

import { getPhase4StubStatus } from "../src/index.js";

describe("phase4 sdk stub", () => {
  it("returns stable stub metadata", () => {
    const status = getPhase4StubStatus();
    expect(status.status).toBe("stub");
    expect(status.language).toBe("typescript");
    expect(status.phase).toBe(4);
    expect(status.capabilities.length).toBeGreaterThanOrEqual(3);
  });
});
