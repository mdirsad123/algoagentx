"use client";

import { FaRegFileLines } from "react-icons/fa6";

const BookingViewDetails = ({ data, mode, onPrint }: { data: any; mode: string; onPrint?: () => void }) => {
  if (!data) return null;

  return (
    <div className="bg-white dark:bg-gray-900 p-6 rounded-lg space-y-6">
      {/* ================= HEADER ================= */}
      <div className="pb-4 flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="text-blue-500 text-2xl mt-1">
            <FaRegFileLines />
          </div>

          <div>
            <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">
              Booking No: {data.booking_no}
            </h1>

            <p className="text-sm text-gray-500">
              Booking Date:{" "}
              {new Date(data.booking_date).toLocaleDateString("en-GB")}
            </p>

            <span className="inline-block mt-2 px-3 py-1 text-sm rounded bg-blue-600 text-white">
              {data.status}
            </span>
          </div>
        </div>

        {/* Print button - only show if onPrint is provided */}
        {onPrint && (
          <div className="print:hidden no-print">
            <button
              onClick={onPrint}
              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded shadow whitespace-nowrap"
            >
              Print Booking Details
            </button>
          </div>
        )}
      </div>

      {/* ================= BOOKING INFO BOX ================= */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        
        <div className="grid grid-cols-2 gap-4 text-sm text-gray-700 dark:text-gray-200">
          <div>
            <strong>Customer Name:</strong> {data.customer?.customer_name}
          </div>

          <div>
            <strong>Company Name:</strong> {data.company?.company_name}
          </div>

          <div>
            <strong>Vehicle Source:</strong> {data.vehicle_source_booking}
          </div>

          <div>
            <strong>Vehicle Number:</strong> {data.vehicle?.vehicle_no}
          </div>

          <div>
            <strong>From Destination:</strong>{" "}
            {data?.fromDestination?.destination || "N/A"}
          </div>

          <div>
            <strong>To Destination:</strong>{" "}
            {data?.toDestination?.destination || "N/A"}
          </div>

          <div>
            <strong>Order No:</strong> {data.products?.[0]?.order?.order_no}
          </div>
        </div>
      </div>

      {/* ================= PRODUCTS ================= */}
      <div>
        <h2 className="text-lg font-semibold mb-3 text-gray-700 dark:text-gray-200">
          Product Details
        </h2>

        <div className="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg">
          <table className="w-full text-sm">
            <thead className="bg-gray-100 dark:bg-gray-800">
              <tr>
                <th className="border px-3 py-2">Item No</th>
                <th className="border px-3 py-2">Product</th>
                <th className="border px-3 py-2">Packages</th>
                <th className="border px-3 py-2">Weight</th>
                <th className="border px-3 py-2">Rate</th>
                <th className="border px-3 py-2">Rate Type</th>
                <th className="border px-3 py-2">KMs</th>
                <th className="border px-3 py-2">Freight</th>
                <th className="border px-3 py-2">Remarks</th>
              </tr>
            </thead>

            <tbody>
              {data.products.map((p: any) => (
                <tr key={p.booking_product_id}>
                  <td className="border px-3 py-2 text-center">
                    {p.booking_item_no}
                  </td>
                  <td className="border px-3 py-2">
                    {p.product?.product_name}
                  </td>
                  <td className="border px-3 py-2 text-right">
                    {p.no_of_packages}
                  </td>
                  <td className="border px-3 py-2 text-right">{p.weight}</td>
                  <td className="border px-3 py-2 text-right">{p.rate}</td>
                  <td className="border px-3 py-2">{p.ratetype?.rate_type}</td>
                  <td className="border px-3 py-2 text-right">{p.kms}</td>
                  <td className="border px-3 py-2 text-right">
                    {p.fright_amount}
                  </td>
                  <td className="border px-3 py-2">{p.remarks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default BookingViewDetails;