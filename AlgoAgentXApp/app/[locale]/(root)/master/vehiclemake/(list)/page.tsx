"use client";

import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import VehiclemakeTable from "../components/vehiclemake-table";

export default function Page() {
  const { data, isLoading } = useFetcher("/vehiclemake/list", "vehiclemakeList");
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
        <h1 className="text-2xl font-semibold text-gray-800">Vehiclemake List</h1>

        <Button
          className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
          onClick={() => router.push("/master/vehiclemake/new")}
        >
          + Add Vehiclemake
        </Button>
      </div> */}

      <div className="p-5">
        <VehiclemakeTable vehiclemakeList={data}/>
      </div>
    </>
  );
}
