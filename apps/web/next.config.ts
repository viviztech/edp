import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  logging: {
    incomingRequests: {
      ignore: [/\/api\/reports\/organizations\/[^/]+\/exports\/[^/]+\/download\//],
    },
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
  experimental: { cpus: 1 },
  async redirects() {
    return [{ source: "/", destination: "/en", permanent: false }];
  },
  async headers() {
    return [{ source: "/:path*", headers: [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
    ] }, { source: "/api/reports/organizations/:org/exports/:id/download/:token", headers: [
      { key: "Referrer-Policy", value: "no-referrer" },
    ] }];
  },
};
export default config;
