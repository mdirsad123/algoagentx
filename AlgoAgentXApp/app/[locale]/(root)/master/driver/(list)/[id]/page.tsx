"use client";

import { useParams } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import DriverViewDetails from "../../components/driver-detailsview";

export default function ViewDriverPage() {
  const param = useParams();

  const { data, isLoading } = useFetcher(
    `/driver/driverbyid/${param.id}`,
    "driver_full_view"
  );

  const handlePrint = () => {
    window.print();
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
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
          
          /* Ensure status badges are visible in print */
          .bg-blue-600,
          .bg-green-600,
          .bg-red-600,
          .bg-gray-200 {
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
            size: A4;
          }
          
          /* Page breaks for better printing */
          .border {
            page-break-inside: avoid;
          }
          
          /* Ensure borders and backgrounds print correctly */
          * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
        }
      `}</style>

      {/* Only this content will be printed */}
      <div id="print-area">
        <DriverViewDetails data={data} onPrint={handlePrint} />
      </div>
    </>
  );
}