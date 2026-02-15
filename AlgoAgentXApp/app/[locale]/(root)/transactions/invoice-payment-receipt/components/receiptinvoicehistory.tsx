"use client";
import { AiOutlineClose } from "react-icons/ai";
import { useForm } from "react-hook-form";
// Replace the following imports with your actual component paths
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";

export default function ReceiptHistory() {
   const router = useRouter();
   
  const form = useForm({
    defaultValues: {
      receiptNo: "",
      receiptDate: "",
      receivedAgainst: "",
      company: "",
      customer: "",
      customerState: "",
      customerStartDate: "",
      product: "",
      grossAmount: "",
      lessTds: "",
      roundOff: "",
      finalAmount: ""
    }
  });

  const historyRows = [
    {
      sno: 1,
      status: "Generated",
      updatedOn: "15/10/2025 10:15 AM",
      updatedBy: "Rahul Singh",
      remark: "Vehicle assigned and loading in progress"
    },
    {
      sno: 2,
      status: "Dispatched",
      updatedOn: "15/10/2025 10:15 AM",
      updatedBy: "Rakesh Sharma",
      remark: "Vehicle assigned and loading in progress"
    }
  ];

 return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999]">

      {/* MAIN POPUP CARD */}
      <div className="bg-white w-[1200px] h-[90vh] rounded-lg shadow-xl flex flex-col overflow-hidden">

        {/* HEADER (sticky) */}
        <div className="sticky top-0 bg-white border-b px-8 py-4 flex justify-between items-center">
          <h2 className="text-lg font-semibold">Receipt History</h2>

          <button
            onClick={() => router.push("/fleet/invoice-payment-receipt")}
            aria-label="Close"
            className="rounded-full p-2 hover:bg-gray-200"
          >
            <AiOutlineClose className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* BODY (scrollable) */}
        <div className="flex-1 overflow-y-auto px-8 py-6">
          <Form {...form}>
            <form className="space-y-8">

              {/* RECEIPT DETAILS */}
              <div>
                <div className="font-semibold text-base mb-2">Receipt Details</div>
                <hr className="mb-4" />

                <div className="grid grid-cols-3 gap-6">

                  <FormField control={form.control} name="receiptNo" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Receipt No</FormLabel>
                      <FormControl>
                        <Select value={field.value}>
                          <SelectTrigger>
                            <SelectValue placeholder="Receipt No" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="1234">23456</SelectItem>
                          </SelectContent>
                        </Select>
                      </FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="receiptDate" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Receipt Date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} className="w-36" />
                      </FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="receivedAgainst" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Received Against</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="company" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Company</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="customer" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Customer</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="customerState" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Customer State</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="customerStartDate" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Customer Start Date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} className="w-36" />
                      </FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="product" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Product</FormLabel>
                      <FormControl>
                        <Select value={field.value}>
                          <SelectTrigger>
                            <SelectValue placeholder="Product" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Organic Fertilizer Bags">
                              Organic Fertilizer Bags
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </FormControl>
                    </FormItem>
                  )} />

                </div>
              </div>

              {/* AMOUNT DETAILS */}
              <div>
                <div className="font-semibold text-base mb-2">Amount Details</div>
                <hr className="mb-4" />

                <div className="grid grid-cols-3 gap-6">

                  <FormField control={form.control} name="grossAmount" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Gross Amount</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="lessTds" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Less TDS</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="roundOff" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Round Off</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="finalAmount" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Final Amount</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                </div>
              </div>

              {/* HISTORY TABLE */}
              <div>
                <div className="font-semibold text-base mb-2 mt-4">History</div>

                <div className="overflow-x-auto mb-8">
                  <table className="min-w-full bg-gray-50 rounded-lg shadow-sm text-sm">
                    <thead>
                      <tr className="text-left font-semibold">
                        <th className="p-2">S.No</th>
                        <th className="p-2">Status</th>
                        <th className="p-2">Status Updated On</th>
                        <th className="p-2">Status Updated By</th>
                        <th className="p-2">Status Updated Remark</th>
                      </tr>
                    </thead>

                    <tbody>
                      {historyRows.map((row: any) => (
                        <tr key={row.sno} className="border-t">
                          <td className="p-2">{row.sno}</td>
                          <td className="p-2">{row.status}</td>
                          <td className="p-2">{row.updatedOn}</td>
                          <td className="p-2">{row.updatedBy}</td>
                          <td className="p-2">{row.remark}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </form>
          </Form>
        </div>

        {/* FOOTER (sticky) */}
        <div className="sticky bottom-0 bg-white border-t px-8 py-4 flex justify-end">
          <Button
            variant="outline"
            onClick={() => router.push("/fleet/invoice-payment-receipt")}
          >
            Close
          </Button>
        </div>

      </div>
    </div>
  );
}
