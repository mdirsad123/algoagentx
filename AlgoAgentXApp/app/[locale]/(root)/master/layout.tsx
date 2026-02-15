"use client";

import React, {
  useState,
  useEffect,
  createContext,
  useContext,
  useCallback,
} from "react";
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
import { RecordCountContext, useRecordCount } from "./use-record-count";

// Create a simple context for record counts

const MasterLayout = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const pathname = usePathname();
  const [recordCounts, setRecordCounts] = useState<Record<string, number>>({});

  const setCount = useCallback((section: string, count: number) => {
    setRecordCounts((prev) => {
      // Only update if the count is different
      if (prev[section] !== count) {
        return {
          ...prev,
          [section]: count,
        };
      }
      return prev;
    });
  }, []);

  // Fetch all counts on initial load using your useFetcher
  const { data: driverData } = useFetcher("/driver/driverlist", "driverList");
  const { data: companyData } = useFetcher(
    "/company/companylist",
    "companyList"
  );
  const { data: customerData } = useFetcher(
    "/customer/customerlist",
    "customerList"
  );
  const { data: supplierData } = useFetcher(
    "/supplier/supplierlist",
    "supplierList"
  );
  const { data: categoryData } = useFetcher(
    "/category/categorylist",
    "categoryList"
  );
  const { data: destinationData } = useFetcher(
    "/destination/destinationlist",
    "destinationlist"
  );
  const { data: vehicleData } = useFetcher(
    "/vehicle/vehiclelist",
    "vehicleList"
  );
  const { data: vehiclemakeData } = useFetcher(
    "/vehiclemake/list",
    "vehiclemakeList"
  );
  const { data: rateContractData } = useFetcher(
    "/ratecontract/ratecontractlist",
    "rateContractList"
  );
  const { data: rateTypeData } = useFetcher(
    "/ratetype/ratetypelist",
    "rateTypeList"
  );

  // Update counts when data loads
  useEffect(() => {
    const newCounts: Record<string, number> = {};

    if (driverData)
      newCounts.driver = Array.isArray(driverData)
        ? driverData.length
        : driverData.data?.length || 0;
    if (companyData)
      newCounts.company = Array.isArray(companyData)
        ? companyData.length
        : companyData.data?.length || 0;
    if (customerData)
      newCounts.customer = Array.isArray(customerData)
        ? customerData.length
        : customerData.data?.length || 0;
    if (supplierData)
      newCounts.supplier = Array.isArray(supplierData)
        ? supplierData.length
        : supplierData.data?.length || 0;
    if (categoryData)
      newCounts.category = Array.isArray(categoryData)
        ? categoryData.length
        : categoryData.data?.length || 0;
    if (destinationData)
      newCounts.destination = Array.isArray(destinationData)
        ? destinationData.length
        : destinationData.data?.length || 0;
    if (vehicleData)
      newCounts.vehicle = Array.isArray(vehicleData)
        ? vehicleData.length
        : vehicleData.data?.length || 0;

    if (vehiclemakeData)
      newCounts.vehiclemake = Array.isArray(vehiclemakeData)
        ? vehiclemakeData.length
        : vehiclemakeData.data?.length || 0;

    if (rateContractData)
      newCounts.ratecontract = Array.isArray(rateContractData)
        ? rateContractData.length
        : rateContractData.data?.length || 0;
    if (rateTypeData)
      newCounts.ratetype = Array.isArray(rateTypeData)
        ? rateTypeData.length
        : rateTypeData.data?.length || 0;

    // Only update if we have new counts
    if (Object.keys(newCounts).length > 0) {
      setRecordCounts((prev) => ({
        ...prev,
        ...newCounts,
      }));
    }
  }, [
    driverData,
    companyData,
    customerData,
    supplierData,
    categoryData,
    destinationData,
    vehicleData,
    vehiclemakeData,
    rateContractData,
    rateTypeData,
  ]);

  const sections = [
    {
      id: "company",
      name: "Company",
      icon: Calendar,
      route: "/master/company",
      newRoute: "/master/company/new",
    },
    {
      id: "customer",
      name: "Customer",
      icon: Calendar,
      route: "/master/customer",
      newRoute: "/master/customer/new",
    },
    {
      id: "supplier",
      name: "Supplier",
      icon: FileText,
      route: "/master/supplier",
      newRoute: "/master/supplier/new",
    },
    {
      id: "category",
      name: "Category",
      icon: ClipboardCheck,
      route: "/master/category",
      newRoute: "/master/category/new",
    },
    {
      id: "destination",
      name: "Destination",
      icon: Receipt,
      route: "/master/destination",
      newRoute: "/master/destination/new",
    },
    {
      id: "driver",
      name: "Driver",
      icon: DollarSign,
      route: "/master/driver",
      newRoute: "/master/driver/new",
    },
    {
      id: "vehicle",
      name: "Vehicle",
      icon: Truck,
      route: "/master/vehicle",
      newRoute: "/master/vehicle/new",
    },
    {
      id: "vehiclemake",
      name: "Vehicle Make",
      icon: Truck,
      route: "/master/vehiclemake",
      newRoute: "/master/vehiclemake/new",
    },
    {
      id: "ratecontract",
      name: "Rate Contract",
      icon: Truck,
      route: "/master/ratecontract",
      newRoute: "/master/ratecontract/new",
    },
    {
      id: "ratetype",
      name: "Rate Type",
      icon: Truck,
      route: "/master/ratetype",
      newRoute: "/master/ratetype/new",
    },

    {
      id: "product",
      name: "Product",
      icon: Truck,
      route: "/master/product",
      newRoute: "/master/product/new",
    },
  ];

  React.useEffect(() => {
    if (pathname === "/master") {
      router.push("/master/company");
    }
  }, [pathname, router]);

  const handleCardClick = (section: any) => {
    router.push(section.route);
  };

  const handleAddClick = (route: string) => {
    router.push(route);
  };

  const getSectionColor = (section: any) => {
    const isActive = pathname.startsWith(`/master/${section.id}`);
    return isActive
      ? "bg-orange-500 text-white border-orange-500"
      : "bg-white text-gray-900 border-gray-200";
  };

  const getCurrentSection = () => {
    const match = pathname.match(/\/master\/(\w+)/);
    return match ? match[1] : "company";
  };

  const currentSection = getCurrentSection();
  const currentSectionData = sections.find((s) => s.id === currentSection);

  const handleBack = () => {
    if (currentSectionData) {
      router.push(currentSectionData.route);
    } else {
      router.back();
    }
  };

  const getFormTitle = () => {
    if (pathname.includes("/new")) return "Add New";
    if (pathname.includes("/edit")) return "Edit";
    return "View";
  };

  // Check if current page is a form page (new/edit/view)
  const isFormPage =
    pathname.includes("/new") ||
    pathname.includes("/edit") ||
    pathname.match(/\/master\/\w+\/\d+$/) !== null;

  if (isFormPage) {
    return (
      <RecordCountContext.Provider value={{ counts: recordCounts, setCount }}>
        <div className="min-h-screen bg-gray-50">
          <div className="bg-white border-b sticky top-0 z-10">
            <div className="w-full px-4 py-4">
              <div className="flex items-center gap-4">
                <button
                  onClick={handleBack}
                  className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition"
                >
                  <ArrowLeft className="w-5 h-5" />
                  <span className="text-sm font-medium">Back</span>
                </button>
                <div className="h-6 w-px bg-gray-300"></div>
                <h1 className="text-lg font-semibold text-gray-900">
                  {getFormTitle()} {currentSectionData?.name}
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
      </RecordCountContext.Provider>
    );
  }

  return (
    <RecordCountContext.Provider value={{ counts: recordCounts, setCount }}>
      <div className="min-h-screen bg-gray-50">
        <div className="bg-white border-b">
          <div className="w-full px-4 py-4">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => handleCardClick(section)}
                  className={`${getSectionColor(
                    section
                  )} rounded-lg p-3 text-left border hover:shadow-md transition`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <h3
                      className={`text-xs font-semibold truncate ${
                        pathname.startsWith(`/master/${section.id}`)
                          ? "text-white"
                          : "text-gray-900"
                      }`}
                    >
                      {section.name}
                    </h3>
                    {pathname.startsWith(`/master/${section.id}`) && (
                      <div className="w-2 h-2 bg-white rounded-full ml-1"></div>
                    )}
                  </div>
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-xs ${
                        pathname.startsWith(`/master/${section.id}`)
                          ? "text-white/90"
                          : "text-gray-600"
                      }`}
                    >
                      {recordCounts[section.id] ?? 0} Records
                    </span>
                    {pathname.startsWith(`/master/${section.id}`) ? (
                      <div className="w-5 h-5 flex items-center justify-center bg-white rounded-full">
                        <ArrowRight className="w-3 h-3 text-orange-500" />
                      </div>
                    ) : (
                      <ArrowRight className="w-3 h-3 text-gray-400" />
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="w-full px-4 py-4">
          <div className="bg-white rounded-lg border shadow-sm">
            <div className="px-4 py-3 border-b flex items-center justify-between">
              <h2 className="text-lg font-semibold">
                {currentSectionData?.name}
              </h2>
              <button
                onClick={() =>
                  handleAddClick(currentSectionData?.newRoute || "")
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
    </RecordCountContext.Provider>
  );
};

export default MasterLayout;
