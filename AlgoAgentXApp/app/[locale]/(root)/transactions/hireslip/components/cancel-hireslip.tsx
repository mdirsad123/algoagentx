'use client'
import React, { useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { cn } from "@/lib/utils";
import router from "next/router";

// Define the schema for Cancel Hire Slip
const hireSlipSchema = z.object({
  hire_slip_no: z.string().min(1, "Hire Slip No is required"),
  hire_slip_date: z.string().min(1, "Hire Slip Date is required"),
  status: z.string().min(1, "Status is required"),
  booking_no: z.string().min(1, "Booking No is required"),
  booking_date: z.string().min(1, "Booking Date is required"),
  customer: z.string().min(1, "Customer is required"),
  company: z.string().min(1, "Company is required"),
  destination_from: z.string().min(1, "Destination From is required"),
  destination_to: z.string().min(1, "Destination To is required"),
  vehicle: z.string().min(1, "Vehicle is required"),
  supplier: z.string().min(1, "Supplier is required"),
  product_name: z.string().min(1, "Product Name is required"),
  description: z.string().optional(),
  cancel_date: z.string().min(1, "Cancel Date is required"),
  cancel_remark: z.string().min(1, "Cancel Remark is required"),
});

type FormInputs = z.infer<typeof hireSlipSchema>;

type HireSlipFormProps = {
  onClose: () => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  hireSlip?: any;
  mode?: 'add' | 'edit' | 'view';
  readOnly?: boolean;
  asDialog?: boolean;
  onSuccess?: () => void;
};

const CancelHireSlip = ({
  onClose,
  open = false,
  onOpenChange,
  hireSlip,
  mode = 'add',
  readOnly = false,
  asDialog = true,
  onSuccess: onSuccessCallback
}: HireSlipFormProps) => {

  const isInitialized = useRef(false);

  const form = useForm<FormInputs>({
    resolver: zodResolver(hireSlipSchema),
    defaultValues: {
      hire_slip_no: "",
      hire_slip_date: "",
      status: "",
      booking_no: "",
      booking_date: "",
      customer: "",
      company: "",
      destination_from: "",
      destination_to: "",
      vehicle: "",
      supplier: "",
      product_name: "",
      description: "",
      cancel_date: "",
      cancel_remark: "",
    },
  });

  const onSubmit = (values: FormInputs) => {
    console.log(values);
    if (onSuccessCallback) {
      onSuccessCallback();
    }
  };
 
  const isReadOnly = readOnly || mode === 'view';


  return (     
    <div className="min-h-screen bg-white dark:bg-gray-950 p-6">
      <div className="w-full px-6 py-4">
        {/* Back Button */}
        <button
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 mb-6 transition-colors text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>

        {/* Heading and Booking List Button */}
        <div className="grid grid-cols-1 md:grid-cols-3 items-center mb-8">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Cancel Hire Slip
          </h1>

          <div className="md:col-start-3 flex justify-end">
            <button
              type="button"
              className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-orange-500 rounded-lg hover:bg-orange-600"
            >
              <Menu className="w-4 h-4" />
              Booking List
            </button>
          </div>
        </div>

        {/* Form Content */}
        <Form {...form}>
        <div className="space-y-6">
          
          {/* First Row - Hire Slip No, Hire Slip Date, Status */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="hire_slip_no"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Hire Slip No.
                  </FormLabel>
                  <FormControl>
                    <Input 
                      {...field} 
                      placeholder="Enter Hire Slip No." 
                      readOnly={isReadOnly}
                      className={cn(
                        "h-11 rounded-lg border border-gray-300 dark:border-gray-700 px-3 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-900",
                        isReadOnly && "bg-gray-50 dark:bg-gray-800 cursor-not-allowed opacity-60"
                      )}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="hire_slip_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Hire Slip Date
                  </FormLabel>
                  <FormControl>
                    <Input 
                      type="date" 
                      {...field} 
                      placeholder="Select Hire Slip Date" 
                      readOnly={isReadOnly}
                      className={cn(
                        "h-11 rounded-lg border border-gray-300 dark:border-gray-700 px-3 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-900",
                        isReadOnly && "bg-gray-50 dark:bg-gray-800 cursor-not-allowed opacity-60"
                      )}
                    />
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
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Status
                  </FormLabel>
                  <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                    <FormControl>
                      <SelectTrigger className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400">
                        <SelectValue placeholder="Select Status" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="cancelled">Cancelled</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Section Title - Booking Details */}
          <div className="pt-4">
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
              Booking Details
            </h2>
          </div>
          
          {/* First Row - Booking No, Booking Date, Customer */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="booking_no"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Booking No.
                  </FormLabel>
                  <FormControl>
                    <Input 
                      {...field} 
                      placeholder="Enter Booking No." 
                      readOnly={isReadOnly}
                      className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 px-3 text-sm bg-white dark:bg-gray-900"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="booking_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Booking Date
                  </FormLabel>
                  <FormControl>
                    <Input 
                      type="date" 
                      {...field} 
                      placeholder="Select Booking Date" 
                      readOnly={isReadOnly}
                      className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 px-3 text-sm bg-white dark:bg-gray-900"
                    />
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
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Customer
                  </FormLabel>
                  <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                    <FormControl>
                      <SelectTrigger className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400">
                        <SelectValue placeholder="Select Customer" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="customer1">Customer 1</SelectItem>
                      <SelectItem value="customer2">Customer 2</SelectItem>
                      <SelectItem value="customer3">Customer 3</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Second Row - Company, Destination From, Destination To */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="company"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Company
                  </FormLabel>
                  <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                    <FormControl>
                      <SelectTrigger className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400">
                        <SelectValue placeholder="Select Company" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="Company1">Company 1</SelectItem>
                      <SelectItem value="Company2">Company 2</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="destination_from"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Destination From
                  </FormLabel>
                  <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                    <FormControl>
                      <SelectTrigger className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400">
                        <SelectValue placeholder="Select Customer" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="Location1">Location 1</SelectItem>
                      <SelectItem value="Location2">Location 2</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="destination_to"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Destination To
                  </FormLabel>
                  <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                    <FormControl>
                      <SelectTrigger className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400">
                        <SelectValue placeholder="Select Company" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="Location1">Location 1</SelectItem>
                      <SelectItem value="Location2">Location 2</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Third Row - Vehicle, Supplier */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="vehicle"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Vehicle
                  </FormLabel>
                  <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                    <FormControl>
                      <SelectTrigger className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400">
                        <SelectValue placeholder="Select Vehicle" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="Vehicle1">Vehicle 1</SelectItem>
                      <SelectItem value="Vehicle2">Vehicle 2</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="supplier"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Supplier
                  </FormLabel>
                  <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                    <FormControl>
                      <SelectTrigger className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400">
                        <SelectValue placeholder="Select Supplier" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="Supplier1">Supplier 1</SelectItem>
                      <SelectItem value="Supplier2">Supplier 2</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Section Title - Product / Package Details */}
          <div className="pt-4">
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
              Product / Package Details
            </h2>
          </div>
          
          {/* Product Name */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="product_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Product Name
                  </FormLabel>
                  <FormControl>
                    <Input 
                      {...field} 
                      placeholder="Enter Product Name" 
                      readOnly={isReadOnly}
                      className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 px-3 text-sm bg-white dark:bg-gray-900"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Description */}
          <div className="grid grid-cols-1 gap-6">
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Description
                  </FormLabel>
                  <FormControl>
                    <Textarea 
                      {...field} 
                      placeholder="Enter Description" 
                      rows={3} 
                      readOnly={isReadOnly}
                      className="rounded-lg border border-gray-300 dark:border-gray-700 px-3 py-2 text-sm bg-white dark:bg-gray-900"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Section Title - Cancel Details */}
          <div className="pt-4">
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
              Cancel Details
            </h2>
          </div>

          {/* Cancel Date and Remark */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField
              control={form.control}
              name="cancel_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Cancel Date
                  </FormLabel>
                  <FormControl>
                    <Input 
                      type="date" 
                      {...field} 
                      placeholder="Select Hire Slip Date" 
                      readOnly={isReadOnly}
                      className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 px-3 text-sm bg-white dark:bg-gray-900"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="cancel_remark"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                    Cancel Remark
                  </FormLabel>
                  <FormControl>
                    <Input 
                      {...field} 
                      placeholder="Enter Remarks" 
                      readOnly={isReadOnly}
                      className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 px-3 text-sm bg-white dark:bg-gray-900"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Form Actions */}
          <div className="flex gap-3 pt-6">
            {!isReadOnly && (
              <Button
                type="button"
                className="h-10 px-6 text-sm font-medium text-white bg-gray-900 dark:bg-gray-800 rounded-lg hover:bg-gray-800 dark:hover:bg-gray-700 focus:outline-none"
              >
                Cancel Hire Slip
              </Button>
            )}
            
            <Button
              type="button"
              variant="outline"
              onClick={() => onClose?.()}
              className="h-10 px-6 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              Close
            </Button>
          </div>
        </div>
      </Form>
      </div>
    </div>
  );
};

export default CancelHireSlip;