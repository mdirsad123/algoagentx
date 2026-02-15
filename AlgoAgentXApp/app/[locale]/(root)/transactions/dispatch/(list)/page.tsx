"use client";

import { useState } from "react";
import FormHeader from "@/components/shared/form-header";
import { Button } from "@/components/ui/button";
import DispatchTable from "../components/dispatch-table";
import AddDispatchForm from "../components/dispatch-form";
import { Building } from "lucide-react";
import { useRouter } from "next/navigation";

export default function Page() {
  const router = useRouter();
  return (
    <div className=" space-y-5">
      <div className="flex items-center justify-between w-full px-5">
        <button className="font-semibold">Dispatched List</button>

        <Button
          className="bg-orange-600 text-white"
           onClick={() => router.push("/fleet/dispatch/new")}
        >
          Add Dispatch
        </Button>
      </div>

      <DispatchTable dispatchList={[]} />

    </div>
  );
}
