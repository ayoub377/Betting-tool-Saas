// src/components/ui/Banner.tsx
"use client"; // Can be a client component if you plan to add interactions later

import React from 'react';

interface BannerProps {
  imageUrl?: string;
  imageAlt?: string;
  title?: string;
  description?: string;
  ctaText?: string; // Optional CTA button text
  ctaHref?: string; // Optional CTA button link
  className?: string;
}

const Banner: React.FC<BannerProps> = ({
  imageUrl = "https://placehold.co/1200x400/e0e7ff/4f46e5?text=Awesome+Product&font=lexend", // A more vibrant placeholder
  imageAlt = "Promotional banner image",
  title = "Showcase Your Amazing Feature!",
  description = "Highlight the key benefits and draw users in with a compelling message. This is where your product shines.",
  ctaText,
  ctaHref,
  className = "",
}) => {
  return (
    <div className={`relative overflow-hidden rounded-lg shadow-lg bg-gray-100 dark:bg-slate-800 ${className}`}>
      {/* Background Image */}
      <div className="absolute inset-0">
        <img
          src={imageUrl}
          alt={imageAlt}
          className="w-full h-full object-cover object-center"
          // Fallback image in case the provided one fails
          onError={(e) => {
            const target = e.target as HTMLImageElement;
            target.onerror = null; // Prevent infinite loop
            target.src = "https://placehold.co/1200x400/e2e8f0/cbd5e0?text=Image+Not+Available";
          }}
        />
        {/* Overlay for text contrast */}
        <div
          className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/40 to-transparent
                     md:bg-gradient-to-r md:from-black/75 md:via-black/30 md:to-transparent"
        ></div>
      </div>

      {/* Text Content - Positioned to the left for a common banner layout */}
      <div className="relative z-10 flex flex-col justify-center h-full min-h-[300px] md:min-h-[400px] p-6 sm:p-8 md:p-12 lg:p-16 text-white max-w-full md:max-w-2xl lg:max-w-3xl">
        <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold mb-3 sm:mb-4 leading-tight">
          {title}
        </h2>
        <p className="text-base sm:text-lg md:text-xl text-gray-200 dark:text-gray-300 mb-6 sm:mb-8 leading-relaxed">
          {description}
        </p>

        {/* Optional Call to Action Button */}
        {ctaText && ctaHref && (
          <div>
            <a
              href={ctaHref}
              className="inline-block px-6 py-3 text-sm sm:text-base font-semibold
                         bg-blue-600 hover:bg-blue-700 dark:bg-sky-500 dark:hover:bg-sky-600
                         text-white rounded-lg shadow-md transition-colors duration-150 ease-in-out
                         focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-black/50 focus-visible:ring-blue-500 dark:focus-visible:ring-sky-400"
            >
              {ctaText}
            </a>
          </div>
        )}
      </div>
    </div>
  );
};

export default Banner;
