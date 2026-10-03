import { describe, expect, it } from "vitest";
import { certificatePath } from "./certificate-security";

const code = "certificate_code_1234567890";

describe("certificate BFF allowlist", () => {
  it("allows only public verification JSON and QR reads", () => {
    expect(certificatePath(["verify", code], "GET"))
      .toBe(`/certificates/verify/${code}`);
    expect(certificatePath(["verify", code, "qr"], "GET"))
      .toBe(`/certificates/verify/${code}/qr`);
  });

  it("rejects mutations, traversal and malformed identifiers", () => {
    expect(certificatePath(["verify", code], "POST")).toBeNull();
    expect(certificatePath(["verify", "..", "auth"], "GET")).toBeNull();
    expect(certificatePath(["verify", "short"], "GET")).toBeNull();
  });
});
