import { webcrypto } from "node:crypto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { documentRequest, prepareApplicationFile, uploadApplicationFile } from "./application-document-client";

afterEach(() => { vi.unstubAllGlobals(); });
const bytes = new TextEncoder().encode("abc");
const file = { name: "private-name-never-sent.pdf", size: bytes.byteLength, type: "application/pdf", arrayBuffer: () => Promise.resolve(bytes.buffer) } as File;

describe("application document client", () => {
  it("hashes the exact immutable bytes and omits filenames from metadata", async () => {
    vi.stubGlobal("crypto", webcrypto);
    const prepared = await prepareApplicationFile(file, ["application/pdf"], 4096);
    expect(prepared).toEqual({ media_type: "application/pdf", byte_size: 3, sha256: "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad" });
    expect(prepared).not.toHaveProperty("name");
  });
  it("rejects incompatible or operationally oversized files before reading their bytes", async () => {
    const read = vi.fn(file.arrayBuffer);
    for (const [allowed, maximum] of [[["image/png"], 4096], [["application/pdf"], 1], [["application/pdf"], 0]] as const) {
      await expect(prepareApplicationFile({ ...file, arrayBuffer: read } as File, allowed, maximum)).rejects.toThrow("invalid_file");
    }
    expect(read).not.toHaveBeenCalled();
  });
  it("sends raw bytes once with CSRF and the exact quoted version, without filename or provider headers", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(Response.json({ csrf_token: "csrf" })).mockResolvedValueOnce(Response.json({ document: { id: "binding" } }));
    vi.stubGlobal("fetch", fetchMock);
    await uploadApplicationFile("/api/applications/scoped/content", file, 3);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "PUT", body: file, headers: { "Content-Type": "application/pdf", "If-Match": '"3"', "x-csrf-token": "csrf" } });
    expect(Object.keys(fetchMock.mock.calls[1][1].headers)).toHaveLength(3);
  });
  it("leaves uncertain commands to explicit reconciliation and never automatically retries", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(Response.json({ csrf_token: "csrf" })).mockRejectedValueOnce(new Error("lost response"));
    vi.stubGlobal("fetch", fetchMock);
    await expect(documentRequest("/api/applications/scoped/documents", "POST", { client_request_id: "same-request" })).rejects.toThrow("lost response");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
