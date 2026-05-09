/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    // The project does not ship a stable eslint config yet. Keep production build focused on compile + tsc.
    ignoreDuringBuilds: true,
  },
  typescript: {
    // tsc --noEmit is used as the production type gate. This avoids the Next checker hanging on duplicated legacy trees.
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
