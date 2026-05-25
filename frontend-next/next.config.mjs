const API_ORIGIN = process.env.FITLIO_API_PROXY_TARGET ?? "http://127.0.0.1:8000";
const API_PREFIXES = [
  "auth",
  "admin",
  "classes",
  "member",
  "members",
  "payments",
  "centers",
  "health",
  "app"
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    optimizePackageImports: ["lucide-react"]
  },
  async rewrites() {
    if (process.env.NEXT_PUBLIC_API_BASE_URL) {
      return [];
    }
    return API_PREFIXES.flatMap((prefix) => [
      { source: `/${prefix}`, destination: `${API_ORIGIN}/${prefix}` },
      { source: `/${prefix}/:path*`, destination: `${API_ORIGIN}/${prefix}/:path*` }
    ]);
  }
};

export default nextConfig;
