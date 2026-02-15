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

type CancelDispatchFormInputs = {
  dispatchDate: string;
  dispatchedNo: string;
  status: string;
  // Booking Details
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
  productName: string;
  description: string;
  // Cancel Details
  cancelDate: string;
  cancelRemark: string;
};

export default function CancelDispatchForm() {
  const form = useForm<CancelDispatchFormInputs>();

  const onSubmit = (values: CancelDispatchFormInputs) => {
    // Your submit/API logic here
    console.log(values);
  };

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="w-full"
      >
         <div className="flex justify-between items-center mb-4">
        {/* Back Button */}
        <button
            type="button"
            onClick={() => window.history.back()}
            className="flex items-center px-3 py-1 border rounded-lg text-gray-700 text-sm hover:bg-gray-100 transition"
        >
            &#8592; Back
        </button>
        {/* Booking List Button */}
        <button
  type="button"
  className="flex items-center px-4 py-2 bg-orange-400 hover:bg-orange-500 text-white rounded-lg font-medium text-sm shadow"
>
  Booking List
</button>
        </div>
        <h2 className="mb-4 text-lg font-semibold">Cancel Dispatch</h2>
        <hr className=" mb-6" />

        {/* Top: Dispatch fields */}
        <div className="grid grid-cols-3 gap-6 mb-6">
          <FormField
            control={form.control}
            name="dispatchDate"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Dispatch Date</FormLabel>
                <FormControl>
                  <Input type="date" placeholder="Select Dispatch Date" {...field} className="w-36"/>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="dispatchedNo"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Dispatched No.</FormLabel>
                <FormControl>
                  <Input placeholder="Enter Dispatched No." {...field} />
                </FormControl>
                <FormMessage />
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
                      <SelectValue placeholder="Select Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="open">Open</SelectItem>
                      <SelectItem value="cancelled">Cancelled</SelectItem>
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* BOOKING DETAILS */}
        <div className="font-semibold text-base my-3">Booking Details</div>
        <div className="grid grid-cols-3 gap-6 mb-6">
          <FormField
            control={form.control}
            name="bookingNo"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Booking No.</FormLabel>
                <FormControl>
                  <Input placeholder="Enter Booking No." {...field} />
                </FormControl>
                <FormMessage />
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
                  <Input type="date" placeholder="Select Booking Date" {...field} className="w-36"/>
                </FormControl>
                <FormMessage />
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
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select Customer" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="c1">Customer 1</SelectItem>
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
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
                      <SelectValue placeholder="Select Company" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="comp1">Company 1</SelectItem>
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
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
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select Customer" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="from1">From 1</SelectItem>
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
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
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select Company" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="to1">To 1</SelectItem>
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
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
                      <SelectValue placeholder="Select Company" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="veh1">Vehicle 1</SelectItem>
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
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
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select Customer" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sup1">Supplier 1</SelectItem>
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
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
                  <Input type="date" placeholder="Select Arrival Date" {...field} className="w-36" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="grid grid-cols-3 gap-6">
          <div>
            <FormField
              control={form.control}
              name="loadDate"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Load Date</FormLabel>
                  <FormControl>
                    <Input type="date" placeholder="Select Load Date" {...field} className="w-36"/>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6 my-6">
          <FormField
            control={form.control}
            name="productName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Product Name</FormLabel>
                <FormControl>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select Vehicle" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="prod1">Product 1</SelectItem>
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="my-6">
          <FormField
            control={form.control}
            name="description"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Description</FormLabel>
                <FormControl>
                  <Input placeholder="Enter Description" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* CANCEL DETAILS */}
        <div className="font-semibold text-base my-3">Cancel Details</div>
        <hr className=" mb-6" /> 
        <div className="grid grid-cols-2 gap-6 mb-8">
          <FormField
            control={form.control}
            name="cancelDate"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Cancel Date</FormLabel>
                <FormControl>
                  <Input type="date" placeholder="Select Cancel Date" {...field} className="w-36"/>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="cancelRemark"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Cancel Remark</FormLabel>
                <FormControl>
                  <Input placeholder="Enter Cancel Remark" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="flex gap-4 mt-8">
          <Button type="submit" className="bg-gray-900 text-white">
            Cancel Dispatch
          </Button>
          <Button type="button" variant="outline">
            Close
          </Button>
        </div>
      </form>
    </Form>
  );
}
