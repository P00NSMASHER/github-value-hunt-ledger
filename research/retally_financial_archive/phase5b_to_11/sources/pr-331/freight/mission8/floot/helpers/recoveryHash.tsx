import { createHash } from "node:crypto";
import type { JsonObject, JsonValue } from "./schema";

export function canonicalizeJson(value: JsonValue): JsonValue {
  if (Array.isArray(value)) return value.map(canonicalizeJson);
  if (value !== null && typeof value === "object") {
    const source = value as JsonObject;
    const out: JsonObject = {};
    for (const key of Object.keys(source).sort()) {
      const child = source[key];
      if (child !== undefined) out[key] = canonicalizeJson(child);
    }
    return out;
  }
  return value;
}

export function recoveryHash(value: JsonValue): string {
  return createHash("sha256").update(JSON.stringify(canonicalizeJson(value))).digest("hex");
}

