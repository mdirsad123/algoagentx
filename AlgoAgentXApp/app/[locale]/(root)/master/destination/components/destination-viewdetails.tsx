"use client";

import { Building2 } from "lucide-react";

const DestinationViewDetails = ({
  data,
  mode,
  onPrint,
}: {
  data: any;
  mode: string;
  onPrint?: () => void;
}) => {
  if (!data) return null;

  return (
    <div className="bg-white dark:bg-gray-900 p-6 rounded-lg space-y-6">
      {/* ================= HEADER ================= */}
      <div className="pb-4 flex items-start justify-between gap-4">

        {/* Print button - only show if onPrint is provided */}
        {onPrint && (
          <div className="print:hidden no-print">
            <button
              onClick={onPrint}
              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded shadow whitespace-nowrap"
            >
              Print Details
            </button>
          </div>
        )}
      </div>

      {/* ================= DESTINATION INFO BOX ================= */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-4 text-gray-700 dark:text-gray-200">
          Destination Information
        </h2>

        <div className="grid grid-cols-2 gap-4 text-sm text-gray-700 dark:text-gray-200">
          <div>
            <strong>Destination Code:</strong> {data.dest_code}
          </div>

          <div>
            <strong>Destination Name:</strong> {data.destination}
          </div>

          <div>
            <strong>Country:</strong> {data.country}
          </div>

          <div>
            <strong>State:</strong> {data.state}
          </div>

          <div>
            <strong>City:</strong> {data.city}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DestinationViewDetails;
