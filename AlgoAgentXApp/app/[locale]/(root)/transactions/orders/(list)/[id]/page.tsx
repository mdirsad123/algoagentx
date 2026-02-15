"use client";

import { Building2 } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import { Button } from "@/components/ui/button";

/* Date formatter */
const formatDate = (date?: string) =>
  date ? new Date(date).toISOString().split("T")[0] : "-";

const Page = () => {
  const param = useParams();
  const router = useRouter();

  const { data, isLoading } = useFetcher(
    `/order/orderviewid/${param.id}`,
    "ordergetbyid"
  );

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-[60vh]">
        <ThreeDots height="80" width="80" color="#4fa94d" />
      </div>
    );
  }

  const order = data?.order;

  return (
    <div className="bg-gray-100 min-h-screen py-6 print:bg-white">
      <div className="max-w-5xl mx-auto">
        {/* HEADER (Hidden in Print) */}
        <div className="flex items-center gap-3 mb-4 print:hidden">
          <Building2 className="w-6 h-6 text-gray-700" />
          <h1 className="text-xl font-semibold text-gray-900">Order Details</h1>
        </div>

        {/* PRINT CARD */}
        <div
          id="print-area"
          className="bg-white rounded-xl shadow-lg p-8 print:shadow-none print:rounded-none"
        >
          {/* TITLE */}
          <div className="border-b pb-4 mb-6 flex justify-between">
            <div>
              <h2 className="text-lg font-bold tracking-wide">ORDER SLIP</h2>
              <p className="text-sm text-gray-500">
                Order No: {order?.order_no || "-"}
              </p>
            </div>

            <div className="text-sm text-right">
              <p>
                <strong>Date:</strong> {formatDate(order?.order_date)}
              </p>
              <p>
                <strong>Status:</strong> {order?.status || "-"}
              </p>
            </div>
          </div>

          {/* ORDER INFO */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-6 mb-8">
            <Info label="Customer" value={order?.customer_name} />
            <Info label="Company" value={order?.company_name} />
            <Info label="Order Source" value={order?.order_source} />
            <Info
              label="From Destination"
              value={order?.from_destination_name}
            />
            <Info label="To Destination" value={order?.to_destination_name} />
            <Info label="Vehicle Source" value={order?.vehicle_source} />
            <Info
              label="Dispatch From"
              value={formatDate(order?.dispatch_from)}
            />
            <Info label="Dispatch To" value={formatDate(order?.dispatch_to)} />
          </div>

          {/* PRODUCT TABLE */}
          {/* PRODUCT TABLE */}
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm border-collapse">
              <thead className="bg-gray-100">
                <tr>
                  <th className="border px-3 py-2 text-left">#</th>
                  <th className="border px-3 py-2 text-left">Product</th>
                  <th className="border px-3 py-2 text-right">Packages</th>
                  <th className="border px-3 py-2 text-right">Weight</th>
                  <th className="border px-3 py-2 text-right">Rate</th>
                  <th className="border px-3 py-2 text-right">KMs</th>
                  <th className="border px-3 py-2 text-right"> Fright Amount</th>
                </tr>
              </thead>

              <tbody>
                {order?.products?.map((p: any, i: number) => (
                  <tr key={p.order_product_id || i}>
                    <td className="border px-3 py-2">{i + 1}</td>
                    <td className="border px-3 py-2">
                      {p.product_name || "-"}
                    </td>
                    <td className="border px-3 py-2 text-right">
                      {p.no_of_packages}
                    </td>
                    <td className="border px-3 py-2 text-right">{p.weight}</td>
                    <td className="border px-3 py-2 text-right">{p.rate}</td>
                    <td className="border px-3 py-2 text-right">{p.kms}</td>
                    <td className="border px-3 py-2 text-right font-semibold">
                      {p.fright_amount}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* ACTION BUTTONS - Right below the table */}
            <div className="flex justify-end gap-3 mt-4 p-3 print:hidden border-t">
              <Button
                variant="outline"
                onClick={() => router.push("/transactions")}
              >
                Close
              </Button>

              <Button variant="outline" onClick={() => window.print()}>
                Print
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Page;

/* INFO COMPONENT */
const Info = ({ label, value }: { label: string; value?: any }) => (
  <div>
    <p className="text-xs text-gray-500">{label}</p>
    <p className="text-sm font-medium">{value || "-"}</p>
  </div>
);
