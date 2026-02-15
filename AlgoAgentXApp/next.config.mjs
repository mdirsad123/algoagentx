/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['lucide-react'],

  // Enable standalone output for Docker
  output: 'standalone',

  // Helps cache-busting after each deploy
  generateBuildId: async () => Date.now().toString(),

  // Ensure Next knows where static assets are
  assetPrefix: '',
  basePath: '',

  // Disable server-side compression if Nginx handles it

  compress: false,

  webpack: (config, { isServer }) => {
    config.cache = false;

    // Optional: reduce build size warnings on prod
    
    if (!isServer) {
      config.optimization.splitChunks = {
        chunks: 'all',
        minSize: 20000,
        maxSize: 244000,
      };
    }

    return config;
  },
};

export default nextConfig;
