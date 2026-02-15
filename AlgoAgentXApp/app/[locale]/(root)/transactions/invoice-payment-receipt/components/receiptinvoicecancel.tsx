"use client"
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

export default function ReceiptCancelForm() {
  const form = useForm();
  const router = useRouter();

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999]">

      {/* POPUP CARD */}
      <div className="bg-white w-[1200px] h-[90vh] rounded-lg shadow-xl flex flex-col overflow-hidden">

        {/* HEADER (sticky) */}
        <div className="sticky top-0 bg-white border-b px-8 py-4 flex justify-between items-center">
          <h2 className="text-lg font-semibold">Receipt Cancel</h2>

          <button
            onClick={() => router.push("/fleet/invoice-payment-receipt")}
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
                <hr className="mb-4" />

                <div className="grid grid-cols-3 gap-6">

                  <FormField control={form.control} name="receiptNo" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Receipt No</FormLabel>
                      <FormControl>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select Receipt No" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="43567">45678</SelectItem>
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
                      <FormControl><Input type="date" {...field} className="w-36" /></FormControl>
                    </FormItem>
                  )} />

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

                  <FormField control={form.control} name="chequeNo" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cheque No</FormLabel>
                      <FormControl>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select Check No" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="5678">6789</SelectItem>
                          </SelectContent>
                        </Select>
                      </FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="chequeDate" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cheque Date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} className="w-36" />
                      </FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="chequeAmount" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cheque Amount</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="bankName" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Bank Name</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="bankBranch" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Bank Branch</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="chequeStatus" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cheque Status</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="receivedAmount" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Received Amount</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="depositOn" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Deposit On</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} className="w-36" />
                      </FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="clearOn" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Clear On</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} className="w-36" />
                      </FormControl>
                    </FormItem>
                  )} />

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

              {/* REMARK */}
              <div>
                <FormField control={form.control} name="remark" render={({ field }) => (
                  <FormItem>
                    <FormLabel>Remark</FormLabel>
                    <FormControl><Input {...field} /></FormControl>
                  </FormItem>
                )} />
              </div>

              {/* CANCEL DETAILS */}
              <div>
                <div className="font-semibold text-base mb-2 mt-6">Cancel Details</div>
                <hr className="mb-4" />

                <div className="grid grid-cols-2 gap-6">

                  <FormField control={form.control} name="cancelDate" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cancel Date</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} className="w-36" />
                      </FormControl>
                    </FormItem>
                  )} />

                  <FormField control={form.control} name="cancelRemark" render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cancel Remark</FormLabel>
                      <FormControl><Input {...field} /></FormControl>
                    </FormItem>
                  )} />

                </div>
              </div>

            </form>
          </Form>
        </div>

        {/* FOOTER (sticky) */}
        <div className="sticky bottom-0 bg-white border-t px-8 py-4 flex gap-4 justify-end">
          <button className="bg-gray-900 text-white px-6 py-2 rounded-lg font-medium">
            Cancel Invoice
          </button>

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
