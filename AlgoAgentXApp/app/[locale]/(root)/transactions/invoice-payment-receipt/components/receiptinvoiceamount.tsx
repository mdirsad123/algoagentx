"use client";
import { AiOutlineClose } from "react-icons/ai";
import { useForm } from "react-hook-form";

import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRouter } from "next/navigation";


export default function InvoiceAmountForm() {
  const form = useForm();
  const router = useRouter();

  const invoiceRows = [
    {
      sno: 1,
      invoiceNo: "INV/2025/0048",
      invoiceDate: "28/10/2025",
      from: "Pune, Maharashtra",
      to: "Chennai, Tamil Nadu",
      particulars: "Freight Charges - Organic Fertilizer Transport",
      ackNo: "ACK/2025/0048",
      ackDate: "28/10/2025",
      invoiceAmount: "₹500,000.00",
      receivedAmount: "₹500,000.00",
    },
    {
      sno: 2,
      invoiceNo: "INV/2025/0048",
      invoiceDate: "28/10/2025",
      from: "Pune, Maharashtra",
      to: "Chennai, Tamil Nadu",
      particulars: "Freight Charges - Organic Fertilizer Transport",
      ackNo: "ACK/2025/0048",
      ackDate: "28/10/2025",
      invoiceAmount: "₹500,000.00",
      receivedAmount: "₹500,000.00",
    },
  ];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999]">

      <div className="bg-white w-[1200px] h-[90vh] rounded-lg shadow-xl flex flex-col overflow-hidden">

        {/* HEADER (sticky) */}
        <div className="sticky top-0 bg-white border-b px-8 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Invoice Amount</h2>

          <button onClick={() => router.push("/fleet/invoice-payment-receipt/new")}
            aria-label="Close"
            className="rounded-full p-2 hover:bg-gray-200 transition"
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
                <hr className="mb-6" />

                <div className="grid grid-cols-3 gap-6">

                  {/* Receipt No */}
                  <FormField control={form.control} name="receiptNo" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Receipt No</FormLabel>
                      <FormControl><Input {...field} placeholder="Receipt No" /></FormControl>
                      <FormMessage />
                    </FormItem>
                  )} />

                  {/* Receipt Date */}
                  <FormField control={form.control} name="receiptDate" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Receipt Date</FormLabel>
                      <FormControl><Input type="date" {...field} className="w-36" /></FormControl>
                      <FormMessage />
                    </FormItem>
                  )} />

                  {/* Received Against */}
                  <FormField control={form.control} name="receivedAgainst" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Received Against</FormLabel>
                      <FormControl><Input {...field} placeholder="Received Against" /></FormControl>
                    </FormItem>
                  )} />

                  {/* Company */}
                  <FormField control={form.control} name="company" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Company</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  {/* Customer */}
                  <FormField control={form.control} name="customer" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Customer</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  {/* Customer State */}
                  <FormField control={form.control} name="customerState" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Customer State</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  {/* Customer Start Date */}
                  <FormField control={form.control} name="customerStartDate" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Customer Start Date</FormLabel>
                      <FormControl><Input type="date" {...field} className="w-36" /></FormControl>
                    </FormItem>
                  )} />

                  {/* Product */}
                  <FormField control={form.control} name="product" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Product</FormLabel>
                      <FormControl>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select Product" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="organic">Organic Fertilizer Bags</SelectItem>
                          </SelectContent>
                        </Select>
                      </FormControl>
                    </FormItem>
                  )} />

                </div>
              </div>

              {/* CHEQUE DETAILS */}
              <div>
                <div className="font-semibold text-base mb-2 mt-6">Cheque Details</div>
                <hr className="mb-4" />

                <div className="grid grid-cols-3 gap-6">

                  {/* Cheque No */}
                  <FormField control={form.control} name="chequeNo" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cheque No</FormLabel>
                      <FormControl>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <SelectTrigger><SelectValue placeholder="Cheque No" /></SelectTrigger>
                          <SelectContent><SelectItem value="1234542">1234542</SelectItem></SelectContent>
                        </Select>
                      </FormControl>
                    </FormItem>
                  )} />

                  {/* Cheque Date */}
                  <FormField control={form.control} name="chequeDate" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cheque Date</FormLabel>
                      <FormControl><Input type="date" {...field} className="w-36" /></FormControl>
                    </FormItem>
                  )} />

                  {/* Cheque Amount */}
                  <FormField control={form.control} name="chequeAmount" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cheque Amount</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  {/* Bank Name */}
                  <FormField control={form.control} name="bankName" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Bank Name</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  {/* Bank Branch */}
                  <FormField control={form.control} name="bankBranch" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Bank Branch</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  {/* Cheque Status */}
                  <FormField control={form.control} name="chequeStatus" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cheque Status</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  {/* Received Amount */}
                  <FormField control={form.control} name="receivedAmount" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Received Amount</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  {/* Deposit On */}
                  <FormField control={form.control} name="depositOn" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Deposit On</FormLabel>
                      <FormControl><Input type="date" {...field} className="w-36" /></FormControl>
                    </FormItem>
                  )} />

                  {/* Clear On */}
                  <FormField control={form.control} name="clearOn" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Clear On</FormLabel>
                      <FormControl><Input type="date" {...field} className="w-36" /></FormControl>
                    </FormItem>
                  )} />

                  {/* Bounce On */}
                  <FormField control={form.control} name="bounceOn" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Bounce On</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                </div>
              </div>

              {/* AMOUNT DETAILS */}
              <div>
                <div className="font-semibold text-base mb-2 mt-6">Amount Details</div>
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

              {/* REMARKS */}
              <div>
                <FormField control={form.control} name="remarks" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Remarks</FormLabel>
                    <FormControl><Input {...field} placeholder="Remarks" /></FormControl>
                  </FormItem>
                )} />
              </div>

              {/* INVOICE TABLE */}
              <div>
                <div className="font-semibold text-base mb-2 mt-6">Invoice Details</div>
                <hr className="mb-4" />

                <div className="overflow-x-auto">
                  <table className="min-w-full bg-gray-50 rounded-lg shadow-sm text-sm">
                    <thead>
                      <tr className="text-left font-semibold">
                        <th className="p-2">S.No</th>
                        <th className="p-2">Invoice No.</th>
                        <th className="p-2">Invoice Date</th>
                        <th className="p-2">From Destination</th>
                        <th className="p-2">To Destination</th>
                        <th className="p-2">Particulars</th>
                        <th className="p-2">ACK No</th>
                        <th className="p-2">ACK Date</th>
                        <th className="p-2">Invoice Amount</th>
                        <th className="p-2">Received Amount</th>
                      </tr>
                    </thead>

                    <tbody>
                      {invoiceRows.map((row, idx) => (
                        <tr key={idx} className="border-t">
                          <td className="p-2">{row.sno}</td>
                          <td className="p-2">{row.invoiceNo}</td>
                          <td className="p-2">{row.invoiceDate}</td>
                          <td className="p-2">{row.from}</td>
                          <td className="p-2">{row.to}</td>
                          <td className="p-2">{row.particulars}</td>
                          <td className="p-2">{row.ackNo}</td>
                          <td className="p-2">{row.ackDate}</td>
                          <td className="p-2">{row.invoiceAmount}</td>
                          <td className="p-2">{row.receivedAmount}</td>
                        </tr>
                      ))}

                      <tr className="bg-gray-200 border-t font-semibold">
                        <td className="p-2" colSpan={8}>Total Received Amount</td>
                        <td className="p-2" colSpan={2}>₹950,000.00</td>
                      </tr>
                    </tbody>

                  </table>
                </div>
              </div>

            </form>
          </Form>

        </div>

        {/* FOOTER (sticky) */}
        <div className="sticky bottom-0 bg-white border-t px-8 py-4 flex justify-end">
          <button
            onClick={() => router.push("/fleet/invoice-payment-receipt")}
            className="border rounded px-6 py-2 text-gray-800 hover:bg-gray-100"
          >
            Close
          </button>
        </div>
      </div>

    </div>
  );
}
