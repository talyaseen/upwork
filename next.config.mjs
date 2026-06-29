/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    // Free Unsplash CDN imagery. The browser loads these at runtime; the build
    // makes no external image calls. A gradient + blur placeholder always sits
    // behind each photo so nothing ever renders broken.
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
};

export default nextConfig;
