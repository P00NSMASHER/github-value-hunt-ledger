export function requireSameOriginMutation(request: Request) {
  const method = request.method.toUpperCase();
  if (method === "GET" || method === "HEAD" || method === "OPTIONS") return;

  const fetchSite = request.headers.get("sec-fetch-site");
  if (fetchSite && fetchSite !== "same-origin") {
    throw new Error("Cross-origin mutation rejected");
  }

  const origin = request.headers.get("origin");
  if (origin) {
    let requestOrigin: string;
    let suppliedOrigin: string;
    try {
      requestOrigin = new URL(request.url).origin;
      suppliedOrigin = new URL(origin).origin;
    } catch {
      throw new Error("Invalid mutation origin");
    }
    if (requestOrigin !== suppliedOrigin) {
      throw new Error("Cross-origin mutation rejected");
    }
  }
}

