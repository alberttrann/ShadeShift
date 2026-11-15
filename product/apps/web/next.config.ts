import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@shadeshift/contracts"],
};

export default nextConfig;
