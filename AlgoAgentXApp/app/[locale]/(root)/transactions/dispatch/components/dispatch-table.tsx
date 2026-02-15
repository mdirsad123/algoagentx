"use client";

import { DataTable } from "@/components/shared/data-table";
import { useForm } from "react-hook-form";
import { Form, FormField, FormItem, FormControl, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select";
import DatePicker from "@/components/ui/date-picker";
import { DispatchColumns } from "../columns";
import { useRouter } from "next/navigation";
import { DispatchType } from "@/types/dispatch-type";

type Props = { dispatchList: DispatchType[] };

export default function DispatchTable({ dispatchList }: Props) {
  const form = useForm();
  const router = useRouter();
  
   const handleRowEdit = (row: DispatchType) => {
    router.push(`/contact/lawfirm/edit/${row.dispatchid}`);
  };

  const handleRowView = (row: DispatchType) => {
    router.push(`/contact/lawfirm/${row.dispatchid}`);
  };

  const handleRowDelete = (row: DispatchType) => {
    router.push(`/contact/lawfirm/delete${row.dispatchid}`);
  };

  return (
    <div className="flex flex-col">
      <section className="px-5">

        <Form {...form}>
        
          <div className="w-full border-2 border-gray-200 rounded-lg p-4">

            {/* ---------------- Row 1 -------------- */}
            <div className="grid grid-cols-4 gap-4 mb-4">

              {/* Dispatch No */}
              <FormField
                control={form.control}
                name="dispatch_no"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input placeholder="Dispatch No" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Dispatch Date */}
              <FormField
                control={form.control}
                name="dispatch_date"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <DatePicker
                        placeholder="Dispatch Date"
                        selected={field.value}
                        onSelect={field.onChange}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Customer */}
              <FormField
                control={form.control}
                name="customer"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Select onValueChange={field.onChange}>
                        <SelectTrigger>
                          <SelectValue placeholder="Customer" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Dispatched">asdasc</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Company */}
              <FormField
                control={form.control}
                name="company"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Select onValueChange={field.onChange}>
                        <SelectTrigger>
                          <SelectValue placeholder="Customer" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Dispatched">sdfdg</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

            </div>

            {/* ---------------- Row 2 -------------- */}
            <div className="grid grid-cols-4 gap-4 mb-4">

              {/* From Location */}
              <FormField
                control={form.control}
                name="from_location"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input placeholder="From Location" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* To Location */}
              <FormField
                control={form.control}
                name="to_location"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input placeholder="To Location" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Product */}
              <FormField
                control={form.control}
                name="product"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Select onValueChange={field.onChange}>
                        <SelectTrigger>
                          <SelectValue placeholder="Product" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Dispatched">oil</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Dispatch Type */}
              <FormField
                control={form.control}
                name="dispatch_type"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Select onValueChange={field.onChange}>
                        <SelectTrigger>
                          <SelectValue placeholder="Dispatch" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Dispatched">AS67DB5678</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

            </div>

            {/* ---------------- Row 3 -------------- */}
            <div className="grid grid-cols-4 gap-4 mb-4">

              {/* Vehicle No */}
              <FormField
                control={form.control}
                name="vehicle_no"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                       <Select onValueChange={field.onChange}>
                        <SelectTrigger>
                          <SelectValue placeholder="Vehicle No." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Dispatched">AS67DB5678</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Status */}
              <FormField
                control={form.control}
                name="status"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Select onValueChange={field.onChange}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select Status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Dispatched">Dispatched</SelectItem>
                          <SelectItem value="Acknowledged">Acknowledged</SelectItem>
                          <SelectItem value="Invoice Generated">Invoice Generated</SelectItem>
                          <SelectItem value="Partial Paid">Partial Paid</SelectItem>
                          <SelectItem value="Paid">Paid</SelectItem>
                          <SelectItem value="Cancelled">Cancelled</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Booking No */}
              <FormField
                control={form.control}
                name="booking_no"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                       <Select onValueChange={field.onChange}>
                        <SelectTrigger>
                        <SelectValue placeholder="Booking No." />
                        </SelectTrigger>
                        <SelectContent>
                        <SelectItem value="booking no">2345</SelectItem>
                        </SelectContent>
                    </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Booking Date */}
              <FormField
                control={form.control}
                name="booking_date"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <DatePicker
                        placeholder="Booking Date"
                        selected={field.value}
                        onSelect={field.onChange}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

            </div>

            <div className="grid grid-cols-4 gap-4 mb-4">
               <FormField
                control={form.control}
                name="hire_slip_no"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                       <Select onValueChange={field.onChange}>
                        <SelectTrigger>
                        <SelectValue placeholder="Hire Slip No." />
                        </SelectTrigger>
                        <SelectContent>
                        <SelectItem value="hire slip no">123</SelectItem>
                        </SelectContent>
                    </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
           
              <FormField
                control={form.control}
                name="hire_slip_dates"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <DatePicker
                        placeholder="Hire Slip Date"
                        selected={field.value}
                        onSelect={field.onChange}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div></div>
            {/* Search Button */}
            {/* <div className="flex justify-end mt-2"> */}
              <button className="px-6 py-2 border rounded-lg">
                Search
              </button>
            </div>

          </div>
        </Form>

        {/* ---------------- DataTable ---------------- */}
        <DataTable
          columns={DispatchColumns({
            //  onEdit: (e) => handleRowEdit(e),
            onView: (e) => handleRowView(e),
            onDelete: (e) => console.log("Delete Dispatch:", e),
          })}
          data={dispatchList}
          showSearch={false}
          showPagination={true}
          paginationOptions={{ showRowCount: true, showPageSize: true }}
          exportOptions={{
            csv: true,
            pdf: true,
            filename: "dispatch",
            title: "Dispatch List",
          }}
        />

      </section>
    </div>
  );
}
