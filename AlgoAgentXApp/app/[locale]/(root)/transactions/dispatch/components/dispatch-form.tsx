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

type DispatchFormInputs = {
  dispatchDate: string;
  hireSlipDate: string;
  hireSlipNo: string;
  // Booking Details
  bookingNo: string;
  bookingDate: string;
  customer: string;
  company: string;
  destinationFrom: string;
  destinationTo: string;
  // Vehicle Details
  vehicle: string;
  supplier: string;
  arrivalDate: string;
  loadDate: string;
  // Product Details
  productName: string;
  rateType: string;
  rate: string;
  // Package Details
  noOfPackages: string;
  tareWeight: string;
  netWeight: string;
  grossAmount: string;
  // Pricing
  kms: string;
  totalAmount: string;
  finalAmount: string;
  // Description
  description: string;
};

export default function AddDispatchForm() {
  const form = useForm<DispatchFormInputs>();

  const onSubmit = (values: DispatchFormInputs) => {
    // Your submit/API logic here
    console.log(values);
  };

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="w-full "
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
        <h2 className="mb-2 text-lg font-semibold">Add Dispatch</h2>
        <hr className=" mb-6" />

        {/* Top: Dispatch and Hire */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
          <FormField
            control={form.control}
            name="dispatchDate"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Dispatch Date</FormLabel>
                <FormControl>
                  <Input type="date" placeholder="Select Dispatch Date" {...field} className="w-36" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="hireSlipDate"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Hire Slip Date</FormLabel>
                <FormControl>
                  <Input type="date" placeholder="Select Hire Slip Date" {...field} className="w-36"/>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="hireSlipNo"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Hire Slip No.</FormLabel>
                <FormControl>
                  <Input placeholder="Enter Hire Slip No." {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* BOOKING DETAILS */}
        <div className="font-semibold text-base my-3">Booking Details</div>
        <hr className=" mb-6" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
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
                      <SelectValue placeholder="Select Destination From" />
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
                      <SelectValue placeholder="Select Destination To" />
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

        {/* VEHICLE DETAILS */}
        <div className="font-semibold text-base my-3">Vehicle Details</div>
        <hr className=" mb-6" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
          <FormField
            control={form.control}
            name="vehicle"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Vehicle</FormLabel>
                <FormControl>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select Vehicle" />
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
                      <SelectValue placeholder="Select Supplier" />
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
                  <Input type="date" placeholder="Select Arrival Date" {...field} className="w-36"/>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* Load Date, as full-width */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
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

        {/* PRODUCT DETAILS */}
        <div className="font-semibold text-base my-3">Product Details</div>
        <hr className=" mb-6" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
          <FormField
            control={form.control}
            name="productName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Product Name</FormLabel>
                <FormControl>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select Product" />
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
          <FormField
            control={form.control}
            name="rateType"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Rate Type</FormLabel>
                <FormControl>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select Rate Type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="perTon">Per Ton</SelectItem>
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="rate"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Rate</FormLabel>
                <FormControl>
                  <Input placeholder="Enter Rate" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        {/* Product Details Table */}
        <div className="overflow-x-auto mb-6">
          <table className="min-w-full bg-gray-50 rounded-lg shadow-sm text-sm">
            <thead>
              <tr className="text-left font-semibold">
                <th className="p-2">S.No</th>
                <th className="p-2">Product Name</th>
                <th className="p-2">Rate Type</th>
                <th className="p-2">Rate</th>
                <th className="p-2">Quantity</th>
                <th className="p-2">Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t">
                <td className="p-2">1</td>
                <td className="p-2">Organic Fertilizer Bags</td>
                <td className="p-2">Per Ton</td>
                <td className="p-2">₹45,000.00</td>
                <td className="p-2">15 Tons</td>
                <td className="p-2">₹7,75,000.00</td>
              </tr>
              {/* Map actual rows here */}
            </tbody>
          </table>
        </div>

        {/* PACKAGE DETAILS */}
        <div className="font-semibold text-base my-3">Package Details</div>
        <hr className=" mb-6" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
          <FormField
            control={form.control}
            name="noOfPackages"
            render={({ field }) => (
              <FormItem>
                <FormLabel>No. of Packages</FormLabel>
                <FormControl>
                  <Input placeholder="Enter No. of Packages" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="tareWeight"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Tare Weight</FormLabel>
                <FormControl>
                  <Input placeholder="Enter Tare Weight" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="netWeight"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Net Weight</FormLabel>
                <FormControl>
                  <Input placeholder="Enter Net Weight" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
          <FormField
            control={form.control}
            name="grossAmount"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Gross Amount</FormLabel>
                <FormControl>
                  <Input placeholder="Enter Gross Amount" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* PRICING */}
        <div className="font-semibold text-base my-3 ">Pricing</div>
        <hr className=" mb-6" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
          <FormField
            control={form.control}
            name="kms"
            render={({ field }) => (
              <FormItem>
                <FormLabel>K.M.S</FormLabel>
                <FormControl>
                  <Input placeholder="Enter KMS" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="totalAmount"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Total Amount</FormLabel>
                <FormControl>
                  <Input placeholder="Enter Total Amount" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="finalAmount"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Final Amount</FormLabel>
                <FormControl>
                  <Input placeholder="Enter Final Amount" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* DESCRIPTION */}
        <div className="mb-8">
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

        <div className="flex gap-4 mt-10">
          <Button type="submit" className="bg-gray-900 text-white">
            Add Dispatch
          </Button>
          <Button type="button" variant="outline">
            Close
          </Button>
        </div>
      </form>
    </Form>
  );
}
