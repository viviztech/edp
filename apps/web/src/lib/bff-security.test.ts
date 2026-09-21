import { describe, expect, it } from "vitest";
import { backendPath, validMutation } from "./bff-security";

describe("BFF security boundary", () => {
  it("requires matching origin and CSRF cookie/header including login", () => {
    expect(validMutation("https://edp.example", "https://edp.example", "token", "token")).toBe(true);
    expect(validMutation("https://evil.example", "https://edp.example", "token", "token")).toBe(false);
    expect(validMutation(null, "https://edp.example", "token", "token")).toBe(false);
    expect(validMutation("https://edp.example", "https://edp.example", "token", null)).toBe(false);
    expect(validMutation("https://edp.example", "https://edp.example", "token", "other")).toBe(false);
  });
  it("accepts the alternate loopback hostname only on the configured local port", () => {
    expect(validMutation("http://localhost:3001", "http://127.0.0.1:3001", "token", "token")).toBe(true);
    expect(validMutation("http://127.0.0.1:3001", "http://localhost:3001", "token", "token")).toBe(true);
    expect(validMutation("http://localhost:3002", "http://127.0.0.1:3001", "token", "token")).toBe(false);
    expect(validMutation("http://localhost.evil.example:3001", "http://127.0.0.1:3001", "token", "token")).toBe(false);
    expect(validMutation("https://localhost:3001", "http://127.0.0.1:3001", "token", "token")).toBe(false);
    expect(validMutation("http://localhost:3001", "https://edp.example", "token", "token")).toBe(false);
    expect(validMutation("http://localhost:3001", "http://127.0.0.1:3001", "token", "other")).toBe(false);
  });
  it("cannot proxy arbitrary paths, refresh credentials, methods or origins", () => {
    expect(backendPath(["login"], "POST")).toBe("/auth/browser/login");
    expect(backendPath(["refresh"], "POST")).toBeNull();
    expect(backendPath(["..", "auth", "login"], "POST")).toBeNull();
    expect(backendPath(["https://evil.example"], "GET")).toBeNull();
    expect(backendPath(["login"], "GET")).toBeNull();
    expect(backendPath(["staff", "invalid"], "GET")).toBeNull();
  });
});
