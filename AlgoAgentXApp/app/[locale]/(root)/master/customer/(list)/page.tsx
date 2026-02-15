"use client";

import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import CustomerTable from "../components/customer-table";

export default function Page() {
  const { data, isLoading } = useFetcher("/Customer/list", "customerList");
  const router = useRouter();

  if (isLoading) {
    return (
      <div className="flex justify-center items-center">
        <section className="p-5">
          <ThreeDots height="80" width="80" color="#4fa94d" />
        </section>
      </div>
    );
  }

  return (
    <>
      {/* <div className="flex items-center justify-between p-5 border-b bg-white">
        <h1 className="text-2xl font-semibold text-gray-800">Customer List</h1>

        <Button
          className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
          onClick={() => router.push("/master/customer/new")}
        >
          + Add Customer
        </Button>
      </div> */}

      {/* Company Table */}
      <div className="p-5">
        <CustomerTable customerList={data} />
      </div>
    </>
  );
}
