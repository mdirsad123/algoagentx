"use client";
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
import React from "react";
import { useForm } from "react-hook-form";

type DispatchedHistoryInputs = {
  dispatchedNo: string;
  dispatchedDate: string;
  status: string;
  // Booking History
  bookingNo: string;
  bookingDate: string;
  customer: string;
  company: string;
  destinationFrom: string;
  destinationTo: string;
  vehicle: string;
  supplier: string;
  arrivalDate: string;
  loadDate: string;
  // Product Details
  productName: string;
  description: string;
};

export default function DispatchedHistoryForm() {
  const form = useForm<DispatchedHistoryInputs>({
    defaultValues: {
      dispatchedNo: "",
      dispatchedDate: "",
      status: "",
      bookingNo: "",
      bookingDate: "",
      customer: "",
      company: "",
      destinationFrom: "",
      destinationTo: "",
      vehicle: "",
      supplier: "",
      arrivalDate: "",
      loadDate: "",
      productName: "",
      description:"",
       },
  });

  // Example history data
  const historyRows = [
    {
      sno: 1,
      status: "Generated",
      updatedOn: "15/10/2025 10:15 AM",
      updatedBy: "Rahul Singh",
      remark: "Vehicle assigned and loading in progress",
    },
    {
      sno: 2,
      status: "Dispatched",
      updatedOn: "15/10/2025 10:15 AM",
      updatedBy: "Rakesh Sharma",
      remark: "Vehicle assigned and loading in progress",
    },
  ];

  return (
    <Form {...form}>
      <form className="w-full ">
       <div className="flex items-center justify-between mb-2">
  <h2 className="text-lg font-semibold">Dispatched History</h2>
  <button
    type="button"
    aria-label="Close"
    onClick={() => {/* your close logic here */}}
    className="rounded-full p-2 hover:bg-gray-200 transition"
  >
    {/* X icon (SVG) */}
    <svg
      className="w-5 h-5 text-gray-600"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      viewBox="0 0 24 24"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  </button>
</div>
        <hr className=" mb-6" />
        {/* Dispatched Header */}
        <div className="grid grid-cols-3 gap-6 mb-6">
          <FormField
            control={form.control}
            name="dispatchedNo"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Dispatched No.</FormLabel>
                <FormControl>
                  <Input readOnly {...field} />
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="dispatchedDate"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Dispatched Date</FormLabel>
                <FormControl>
                  <Input type="date" readOnly {...field} className="w-36"/>
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="status"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Status</FormLabel>
                <FormControl>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="generated">Generated</SelectItem>
                    </SelectContent>
                  </Select>
                </FormControl>
              </FormItem>
            )}
          />
        </div>

        {/* Booking History Header */}
        <div className="font-semibold text-base my-3">Booking History</div>
        <hr className=" mb-6" />
        {/* Booking History Fields */}
        <div className="grid grid-cols-3 gap-6 mb-6">
          <FormField
            control={form.control}
            name="bookingNo"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Booking No.</FormLabel>
                <FormControl>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="129403858357">129403858357</SelectItem>
                    </SelectContent>
                  </Select>
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="bookingDate"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Booking Date</FormLabel>
                <FormControl>
                  <Input type="date" readOnly {...field} className="w-36"/>
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="customer"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Customer</FormLabel>
                <FormControl>
                  <Input readOnly {...field} />
                </FormControl>
              </FormItem>
            )}
          />
        </div>
        <div className="grid grid-cols-3 gap-6 mb-6">
          <FormField
            control={form.control}
            name="company"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Company</FormLabel>
                <FormControl>
                   <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="33">33kuber</SelectItem>
                    </SelectContent>
                  </Select>
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="destinationFrom"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Destination From</FormLabel>
                <FormControl>
                  <Input readOnly {...field} />
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="destinationTo"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Destination To</FormLabel>
                <FormControl>
                  <Input readOnly {...field} />
                </FormControl>
              </FormItem>
            )}
          />
        </div>
        <div className="grid grid-cols-3 gap-6 mb-6">
          <FormField
            control={form.control}
            name="vehicle"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Vehicle</FormLabel>
                <FormControl>
                   <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="vehicle">Ap23f0943</SelectItem>
                    </SelectContent>
                  </Select>
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="supplier"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Supplier</FormLabel>
                <FormControl>
                  <Input readOnly {...field} />
                </FormControl>
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="arrivalDate"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Arrival Date</FormLabel>
                <FormControl>
                  <Input type="date" readOnly {...field} className="w-36"/>
                </FormControl>
              </FormItem>
            )}
          />
        </div>
        <div className="grid grid-cols-3 gap-6 mb-6">
          <FormField
            control={form.control}
            name="loadDate"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Load Date</FormLabel>
                <FormControl>
                  <Input type="date" readOnly {...field} className="w-36"/>
                </FormControl>
              </FormItem>
            )}
          />
        </div>

        {/* Product Details Header */}
        <div className="font-semibold text-base my-3">Product Details</div>
        <hr className=" mb-6" />
        <div className="grid grid-cols-2 gap-6 mb-6">
          <FormField
            control={form.control}
            name="productName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Product Name</FormLabel>
                <FormControl>
                  <Input readOnly {...field} />
                </FormControl>
              </FormItem>
            )}
          />
        </div>
        <div className="mb-6">
          <FormField
            control={form.control}
            name="description"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Description</FormLabel>
                <FormControl>
                  <Input readOnly {...field} />
                </FormControl>
              </FormItem>
            )}
          />
        </div>

        {/* History Table */}
        <div className="font-semibold text-base my-3">History</div>
        <div className="overflow-x-auto mb-8">
          <table className="min-w-full bg-gray-50 rounded-lg shadow-sm text-sm">
            <thead>
              <tr className="text-left font-semibold">
                <th className="p-2">S.No</th>
                <th className="p-2">Status</th>
                <th className="p-2">Status Updated on</th>
                <th className="p-2">Status Updated By</th>
                <th className="p-2">Status Updated Remark</th>
              </tr>
            </thead>
            <tbody>
              {historyRows.map((row) => (
                <tr className="border-t" key={row.sno}>
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

        <div className="flex gap-4">
          <Button type="button" variant="outline">
            Close
          </Button>
        </div>
      </form>
    </Form>
  );
}
