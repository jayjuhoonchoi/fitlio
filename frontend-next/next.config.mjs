const API_ORIGIN = process.env.FITLIO_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

/** FastAPI JSON/API routes (same-origin proxy in k8s: web → api service). */
const API_PREFIXES = [
  "auth",
  "admin",
  "member",
  "members",
  "payments",
  "centers",
  "messages",
  "classes",
  "bookings",
  "check-in",
  "attendances",
  "api",
  "health"
];

/** Legacy Jinja HTML (tablet kiosk, center landing, static assets). */
const LEGACY_HTML_PREFIXES = ["center", "assets", "legacy"];

const LEGACY_HTML_PATHS = [
  { source: "/app/tablet/:path*", destination: `${API_ORIGIN}/app/tablet/:path*` }
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    optimizePackageImports: ["lucide-react"]
  },
  async rewrites() {
    if (process.env.NEXT_PUBLIC_API_BASE_URL) {
      return [];
    }

    const apiRewrites = API_PREFIXES.flatMap((prefix) => [
      { source: `/${prefix}`, destination: `${API_ORIGIN}/${prefix}` },
      { source: `/${prefix}/:path*`, destination: `${API_ORIGIN}/${prefix}/:path*` }
    ]);

    const legacyRewrites = LEGACY_HTML_PREFIXES.flatMap((prefix) => [
      { source: `/${prefix}`, destination: `${API_ORIGIN}/${prefix}` },
      { source: `/${prefix}/:path*`, destination: `${API_ORIGIN}/${prefix}/:path*` }
    ]);

    return [...apiRewrites, ...legacyRewrites, ...LEGACY_HTML_PATHS];
  }
};

export default nextConfig;
