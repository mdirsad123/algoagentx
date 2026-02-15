"use client";

import { useParams } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import BookingViewDetails from "../../components/bookingview-details";

const Page = () => {
  const param = useParams();
  const { data, isLoading } = useFetcher(
    `/transaction/booking/${param.id}`,
    `booking-${param.id}`
  );

  const handlePrint = () => {
    window.print();
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center">
        <ThreeDots height="80" width="80" color="#4fa94d" />
      </div>
    );
  }

  return (
    <>
      <style jsx global>{`
        @media print {
          /* Hide everything by default */
          body * {
            visibility: hidden;
          }
          
          /* Only show the print area and its children */
          #print-area,
          #print-area * {
            visibility: visible;
          }
          
          /* Position print area at top left */
          #print-area {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
          }
          
          /* Hide navbar, sidebar, headers, footers */
          nav,
          header,
          footer,
          .sidebar,
          .no-print {
            display: none !important;
          }
          
          /* Remove shadows and adjust colors for print */
          .bg-gray-900 {
            background-color: white !important;
            color: black !important;
          }
          
          .dark\\:bg-gray-900 {
            background-color: white !important;
          }
          
          .dark\\:text-gray-100,
          .dark\\:text-gray-200 {
            color: black !important;
          }
          
          /* Ensure status badge is visible in print */
          .bg-blue-600 {
            background-color: #2563eb !important;
            color: white !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          
          /* Ensure table borders are visible */
          table,
          th,
          td {
            border: 1px solid #000 !important;
          }
          
          /* Remove page margins */
          @page {
            margin: 0.5cm;
          }
        }
      `}</style>

      {/* Only this content will be printed */}
      <div id="print-area">
        <BookingViewDetails data={data?.booking} mode="view" onPrint={handlePrint} />
      </div>
    </>
  );
};

export default Page;