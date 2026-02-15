"use client";

import React from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  ArrowRight,
  Plus,
  Calendar,
  FileText,
  Truck,
  ClipboardCheck,
  Receipt,
  DollarSign,
  ArrowLeft,
} from "lucide-react";
import { useFetcher } from "@/hooks/use-query";

const VehicleLogisticsLayout = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const router = useRouter();
  const pathname = usePathname();

  /* ================= SECTIONS ================= */
  const sections = [
    {
      id: "orders",
      name: "Orders",
      icon: Calendar,
      route: "/transactions/orders",
      newRoute: "/transactions/orders/new",
    },
    {
      id: "bookings",
      name: "Booking Details",
      icon: Calendar,
      route: "/transactions/bookings",
      newRoute: "/transactions/bookings/new",
    },
    {
      id: "hireslip",
      name: "Hire Slip",
      icon: FileText,
      route: "/transactions/hireslip",
      newRoute: "/transactions/hireslip/new",
    },
    {
      id: "dispatch",
      name: "Dispatch Details",
      icon: Truck,
      route: "/transactions/dispatch",
      newRoute: "/transactions/dispatch/new",
    },
    {
      id: "acknowledgment",
      name: "Acknowledgment",
      icon: ClipboardCheck,
      route: "/transactions/acknowledgment",
      newRoute: "/transactions/acknowledgment/new",
    },
    {
      id: "invoicedetails",
      name: "Invoice Details",
      icon: Receipt,
      route: "/transactions/invoicedetails",
      newRoute: "/transactions/invoicedetails/new",
    },
    {
      id: "invoice-payment-receipt",
      name: "Invoice Payment Receive",
      icon: DollarSign,
      route: "/transactions/invoice-payment-receipt",
      newRoute: "/transactions/invoice-payment-receipt/new",
    },
  ];

  /* ================= FETCH COUNTS ================= */
  const { data: ordersData } = useFetcher("/orders/list", "ordersList");
  const { data: bookingsData } = useFetcher("/bookings/bookinglist", "bookingsList");
  const { data: hireslipData } = useFetcher("/hireslip/list", "hireslipList");
  const { data: dispatchData } = useFetcher("/dispatch/list", "dispatchList");
  const { data: acknowledgmentData } = useFetcher(
    "/acknowledgment/list",
    "acknowledgmentList"
  );
  const { data: invoiceData } = useFetcher(
    "/invoicedetails/list",
    "invoiceDetailsList"
  );
  const { data: paymentReceiptData } = useFetcher(
    "/invoice-payment-receipt/list",
    "invoicePaymentReceiptList"
  );

  /* ================= RECORD COUNTS ================= */
  const recordCounts: Record<string, number> = {
    orders: Array.isArray(ordersData)
      ? ordersData.length
      : ordersData?.data?.length || 0,

    bookings: Array.isArray(bookingsData)
      ? bookingsData.length
      : bookingsData?.data?.length || 0,

    hireslip: Array.isArray(hireslipData)
      ? hireslipData.length
      : hireslipData?.data?.length || 0,

    dispatch: Array.isArray(dispatchData)
      ? dispatchData.length
      : dispatchData?.data?.length || 0,

    acknowledgment: Array.isArray(acknowledgmentData)
      ? acknowledgmentData.length
      : acknowledgmentData?.data?.length || 0,

    invoicedetails: Array.isArray(invoiceData)
      ? invoiceData.length
      : invoiceData?.data?.length || 0,

    "invoice-payment-receipt": Array.isArray(paymentReceiptData)
      ? paymentReceiptData.length
      : paymentReceiptData?.data?.length || 0,
  };

  /* ================= REDIRECT ================= */
  React.useEffect(() => {
    if (pathname === "/transactions") {
      router.push("/transactions/bookings");
    }
  }, [pathname, router]);

  /* ================= HELPERS ================= */
  const isFormPage =
    pathname.includes("/new") ||
    pathname.includes("/edit") ||
    pathname.includes("/view") ||
    pathname.match(/\/\d+$/) !== null;

  const currentSection = sections.find((s) =>
    pathname.startsWith(s.route)
  );

  const getFormTitle = () => {
    if (pathname.includes("/new")) return "Add New";
    if (pathname.includes("/edit")) return "Edit";
    return "View";
  };

  const getSectionColor = (section: any) => {
    const isActive = pathname.startsWith(section.route);
    return isActive
      ? "bg-orange-500 text-white border-orange-500"
      : "bg-white text-gray-900 border-gray-200";
  };

  /* ================= FORM PAGE ================= */
  if (isFormPage) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="bg-white border-b sticky top-0 z-10">
          <div className="w-full px-4 py-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.back()}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition"
              >
                <ArrowLeft className="w-5 h-5" />
                <span className="text-sm font-medium">Back</span>
              </button>
              <div className="h-6 w-px bg-gray-300" />
              <h1 className="text-lg font-semibold text-gray-900">
                {getFormTitle()} {currentSection?.name}
              </h1>
            </div>
          </div>
        </div>

        <div className="w-full p-4">
          <div className="bg-white rounded-lg border shadow-sm">
            <div className="p-6">{children}</div>
          </div>
        </div>
      </div>
    );  
  }

  /* ================= LIST PAGE ================= */
  return (
    <div className="min-h-screen bg-gray-50">
      {/* SECTION CARDS */}
      <div className="bg-white border-b">
        <div className="w-full px-4 py-4">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
            {sections.map((section) => {
              const isActive = pathname.startsWith(section.route);

              return (
                <button
                  key={section.id}
                  onClick={() => router.push(section.route)}
                  className={`${getSectionColor(
                    section
                  )} rounded-lg p-3 text-left border hover:shadow-md transition`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <h3
                      className={`text-xs font-semibold truncate ${
                        isActive ? "text-white" : "text-gray-900"
                      }`}
                    >
                      {section.name}
                    </h3>
                    {isActive && (
                      <div className="w-2 h-2 bg-white rounded-full ml-1" />
                    )}
                  </div>

                  <div className="flex items-center justify-between">
                    <span
                      className={`text-xs ${
                        isActive ? "text-white/90" : "text-gray-600"
                      }`}
                    >
                      {recordCounts[section.id] ?? 0} Records
                    </span>

                    {isActive ? (
                      <div className="w-5 h-5 flex items-center justify-center bg-white rounded-full">
                        <ArrowRight className="w-3 h-3 text-orange-500" />
                      </div>
                    ) : (
                      <ArrowRight className="w-3 h-3 text-gray-400" />
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* LIST CONTAINER */}
      <div className="w-full px-4 py-4">
        <div className="bg-white rounded-lg border shadow-sm">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <h2 className="text-lg font-semibold">
              {currentSection?.name}
            </h2>

            <button
              onClick={() =>
                currentSection?.newRoute &&
                router.push(currentSection.newRoute)
              }
              className="bg-orange-500 text-white px-3 py-2 rounded-lg hover:bg-orange-600 transition flex items-center gap-2 text-sm"
            >
              <Plus className="w-4 h-4" />
              Add New
            </button>
          </div>

          <div className="p-0">{children}</div>
        </div>
      </div>
    </div>
  );
};

export default VehicleLogisticsLayout;
