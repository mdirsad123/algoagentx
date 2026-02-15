
"use client";

import { useState } from "react";
import FormHeader from "@/components/shared/form-header";
import { Button } from "@/components/ui/button";
import { Building } from "lucide-react";
import { useRouter } from "next/navigation";
import InvoiceReceiptTable from "../components/receiptinvoice-table";

export default function Page() {
  const router = useRouter();
  return (
    <div className=" space-y-5">
      <div className="flex items-center justify-between w-full px-5">
        <button className="font-semibold">Invoice Receipt List</button>

        <Button
          className="bg-orange-600 text-white"
           onClick={() => router.push("/fleet/invoice-payment-receipt/new")}
        >
          Add Receipt
        </Button>
      </div>

      <InvoiceReceiptTable ReceiptList={[]} />

    </div>
  );
}
