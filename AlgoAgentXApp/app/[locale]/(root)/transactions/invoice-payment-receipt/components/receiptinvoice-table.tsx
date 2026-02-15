"use client";

import { DataTable } from "@/components/shared/data-table";
import { useForm } from "react-hook-form";
import { Form, FormField, FormItem, FormControl, FormMessage } from "@/components/ui/form";

import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select";
import DatePicker from "@/components/ui/date-picker";
import { ReceiptColumns } from "../columns";
import { InvoicePaymentReceiptType } from "@/types/invoicepaymentreceipt-type";

type Props = { ReceiptList: InvoicePaymentReceiptType[] };

export default function InvoiceReceiptTable({ ReceiptList }: Props) {
  const form = useForm();

  return (
    <div className="flex flex-col">
      <section className="px-5">

        <Form {...form}>
          <div className="w-full border-2 border-gray-300 rounded-lg p-4">
            
            {/* ============= ROW 1 ============= */}
            <div className="grid grid-cols-4 gap-4 mb-4">
                 {/* Received Against */}
              <FormField
                control={form.control}
                name="received_against"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                     <Select onValueChange={field.onChange}>
                        <SelectTrigger>
                          <SelectValue placeholder="Received Against for" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="invoice">asdf</SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Receipt No */}
              <FormField
                control={form.control}
                name="receipt_no"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input placeholder="Receipt No." {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

                <FormField
                control={form.control}
                name="Receipt Dates"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <DatePicker
                        placeholder="Receipt Date"
                        selected={field.value}
                        onSelect={field.onChange}
                      />
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
            </div>

            {/* ============= ROW 2 ============= */}
            <div className="grid grid-cols-4 gap-4 mb-4">

                
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
                          <SelectItem value="receipt">sdfdg</SelectItem>
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
                        <SelectValue placeholder="Company" />
                        </SelectTrigger>
                        <SelectContent>
                        <SelectItem value="receipt">sdfdg</SelectItem>
                        </SelectContent>
                    </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

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
            </div>

        {/* ============= ROW 3 ============= */}
            <div className="grid grid-cols-4 gap-4 mb-4">
              {/* Product */}
              <FormField
                control={form.control}
                name="product"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                       <Select onValueChange={field.onChange}>
                        <SelectTrigger>
                        <SelectValue placeholder="Products" />
                        </SelectTrigger>
                        <SelectContent>
                        <SelectItem value="products">sdfdg</SelectItem>
                        </SelectContent>
                    </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

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
                        <SelectItem value="vehicle">23456</SelectItem>
                        </SelectContent>
                    </Select>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

               <FormField
                control={form.control}
                name="invoice_no"
                render={({ field }) => (
                <FormItem>
                    <FormControl>
                     <Select onValueChange={field.onChange}>
                        <SelectTrigger>
                        <SelectValue placeholder="Invoice No." />
                        </SelectTrigger>
                        <SelectContent>
                        <SelectItem value="Invoice">3467</SelectItem>
                        </SelectContent>
                    </Select>
                    </FormControl>
                    <FormMessage />
                </FormItem>
                )}
            />

            {/* Dispatch Date */}
            <FormField
                control={form.control}
                name="Invoice_date"
                render={({ field }) => (
                <FormItem>
                    <FormControl>
                    <DatePicker
                        placeholder="Invoice Date"
                        selected={field.value}
                        onSelect={field.onChange}
                    />
                    </FormControl>
                    <FormMessage />
                </FormItem>
                )}
            />
        </div>

        
            {/* ============= ROW 4 ============= */}
            <div className="grid grid-cols-4 gap-4 mb-4">
            <FormField
            control={form.control}
            name="ack_no"
            render={({ field }) => (
            <FormItem>
            <FormControl>
            <Select onValueChange={field.onChange}>
                <SelectTrigger>
                <SelectValue placeholder="Acknowledgment No." />
                </SelectTrigger>
                <SelectContent>
                <SelectItem value="ack">213456</SelectItem>
                </SelectContent>
            </Select>
            </FormControl>
            <FormMessage />
            </FormItem>
            )}
            />

            {/* Dispatch Date */}
            <FormField
            control={form.control}
            name="ack_date"
            render={({ field }) => (
            <FormItem>
            <FormControl>
                <DatePicker
                placeholder="Acknowledgment Date"
                selected={field.value}
                onSelect={field.onChange}
                />
            </FormControl>
            <FormMessage />
            </FormItem>
            )}
            />

              {/* Dispatch No */}
              <FormField
                control={form.control}
                name="dispatch_no"
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                       <Select onValueChange={field.onChange}>
                        <SelectTrigger>
                        <SelectValue placeholder="Dispatch No." />
                        </SelectTrigger>
                        <SelectContent>
                        <SelectItem value="receipt">34567</SelectItem>
                        </SelectContent>
                    </Select>
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
                        <SelectItem value="hireslipno">1234</SelectItem>
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
                        <SelectItem value="booking no">123</SelectItem>
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
            {/* SEARCH BUTTON */}
            <div className="grid grid-cols-4 gap-4 mb-4">  
            <div></div><div></div><div></div>            
            <button className="px-6 py-2 border rounded-lg">
                Search
              </button>
            </div>

          </div>
        </Form>

        {/* TABLE */}
        <DataTable
          columns={ReceiptColumns({
            onEdit: (e) => console.log("edit", e),
            onView: (e) => console.log("view", e),
            onHistory: (e) => console.log("history", e),
            onCancel: (e) => console.log("cancel", e),
            onChequeStatus: (e) => console.log("cheque", e),
          })}
          data={ReceiptList}
          showSearch={false}
          showPagination={true}
          paginationOptions={{ showRowCount: true, showPageSize: true }}
          exportOptions={{
            csv: true,
            pdf: true,
            filename: "Receipt",
            title: "Receipt List",
          }}
        />

      </section>
    </div>
  );
}
