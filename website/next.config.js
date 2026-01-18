/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  env: {
    NEXT_PUBLIC_CLOUDFRONT_URL: process.env.NEXT_PUBLIC_CLOUDFRONT_URL || '',
    NEXT_PUBLIC_PHOTOS_BUCKET: process.env.PHOTOS_BUCKET || 'yeshvant-photos-storage-2026',
  },
}

module.exports = nextConfig
