export default function Loading() {
  return (
    <div className="p-6 space-y-6 bg-gray-50 min-h-screen">
      {/* Header Skeleton */}
      <div className="flex items-center justify-between">
        <div className="h-8 bg-gray-300 rounded w-48 animate-pulse"></div>
      </div>

      {/* Filters Skeleton */}
      <div className="bg-white p-6 rounded-lg shadow-sm space-y-4">
        <div className="h-6 bg-gray-300 rounded w-32 animate-pulse"></div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="h-4 bg-gray-300 rounded w-20 animate-pulse"></div>
              <div className="h-10 bg-gray-300 rounded animate-pulse"></div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="h-4 bg-gray-300 rounded w-24 animate-pulse"></div>
              <div className="h-10 bg-gray-300 rounded animate-pulse"></div>
            </div>
          ))}
          <div className="flex gap-2 pt-6">
            <div className="h-10 bg-gray-300 rounded w-24 animate-pulse"></div>
            <div className="h-10 bg-gray-300 rounded w-16 animate-pulse"></div>
          </div>
        </div>
      </div>

      {/* Table Skeleton */}
      <div className="bg-white p-6 rounded-lg shadow-sm">
        <div className="h-6 bg-gray-300 rounded w-40 mb-4 animate-pulse"></div>

        {/* Table Header */}
        <div className="grid grid-cols-11 gap-4 mb-4">
          {[...Array(11)].map((_, i) => (
            <div key={i} className="h-4 bg-gray-300 rounded animate-pulse"></div>
          ))}
        </div>

        {/* Table Rows */}
        {[...Array(10)].map((_, rowIndex) => (
          <div key={rowIndex} className="grid grid-cols-11 gap-4 mb-3">
            {[...Array(11)].map((_, colIndex) => (
              <div key={colIndex} className="h-4 bg-gray-300 rounded animate-pulse"></div>
            ))}
          </div>
        ))}

        {/* Pagination */}
        <div className="flex items-center justify-between mt-6">
          <div className="h-4 bg-gray-300 rounded w-32 animate-pulse"></div>
          <div className="flex gap-2">
            <div className="h-8 bg-gray-300 rounded w-20 animate-pulse"></div>
            <div className="h-8 bg-gray-300 rounded w-20 animate-pulse"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
