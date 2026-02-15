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
import { useRouter } from "next/navigation";

// Define the schema based on the form fields shown
const hireSlipSchema = z.object({
  hire_slip_date: z.string().min(1, "Hire Slip Date is required"),
  booking_no: z.string().min(1, "Booking No is required"),
  booking_date: z.string().min(1, "Booking Date is required"),
  customer: z.string().min(1, "Customer is required"),
  company: z.string().min(1, "Company is required"),
  destination_from: z.string().min(1, "Destination From is required"),
  destination_to: z.string().min(1, "Destination To is required"),
  vehicle: z.string().min(1, "Vehicle is required"),
  supplier: z.string().min(1, "Supplier is required"),
  product_name: z.string().min(1, "Product Name is required"),
  no_of_packages: z.string().min(1, "No. of Packages is required"),
  lr_no: z.string().min(1, "LR No. is required"),
  lr_date: z.string().min(1, "LR Date is required"),
  rate_type: z.string().min(1, "Rate Type is required"),
  rate: z.string().min(1, "Rate is required"),
  weight: z.string().min(1, "Weight is required"),
  freight_amount: z.string().min(1, "Freight Amount is required"),
  tds: z.string().optional(),
  advance: z.string().optional(),
  balance: z.string().optional(),
  description: z.string().optional(),
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

const HireSlipForm = ({
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
      hire_slip_date: "",
      booking_no: "",
      booking_date: "",
      customer: "",
      company: "",
      destination_from: "",
      destination_to: "",
      vehicle: "",
      supplier: "",
      product_name: "",
      no_of_packages: "",
      lr_no: "",
      lr_date: "",
      rate_type: "",
      rate: "",
      weight: "",
      freight_amount: "",
      tds: "",
      advance: "",
      balance: "",
      description: "",
    },
  });

  const { handleSubmit, reset } = form;
  const router = useRouter();

  const setFormValue = () => {
    if (hireSlip) {
      reset(hireSlip);
    } else {
      reset({
        hire_slip_date: "",
        booking_no: "",
        booking_date: "",
        customer: "",
        company: "",
        destination_from: "",
        destination_to: "",
        vehicle: "",
        supplier: "",
        product_name: "",
        no_of_packages: "",
        lr_no: "",
        lr_date: "",
        rate_type: "",
        rate: "",
        weight: "",
        freight_amount: "",
        tds: "",
        advance: "",
        balance: "",
        description: "",
      });
    }
  };

  const onSubmit = (values: FormInputs) => {
    console.log(values);
    if (onSuccessCallback) {
      onSuccessCallback();
    }
    handleClose();
  };

  const handleClose = () => {
    if (onOpenChange) {
      onOpenChange(false);
    }
    reset();
    isInitialized.current = false;
    onClose?.();
  };
 
  const isReadOnly = readOnly || mode === 'view';

  useEffect(() => {
    if (asDialog) {
      if (open && !isInitialized.current) {
        setFormValue();
        isInitialized.current = true;
      } else if (!open) {
        isInitialized.current = false;
      }
    } else {
      if (!isInitialized.current) {
        setFormValue();
        isInitialized.current = true;
      }
    }
  }, [open, hireSlip?.id]);

   const handlecancel = () => {
    router.push('/hireslip/cancel-hireslip');
  };

  return (     
    <div className="min-h-screen bg-white dark:bg-gray-950 p-6">
      <div className="w-full px-6 py-4">
        {/* Back Button */}
        <button
          onClick={handleClose}
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 mb-6 transition-colors text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>

        {/* Heading and Booking List Button */}
        <div className="grid grid-cols-1 md:grid-cols-3 items-center mb-8">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Add Hire Slip
          </h1>

          <div className="md:col-start-3 flex justify-end">
            <button
              type="button"
              className="flex items-center gap-2 px-3 py-3 text-sm font-medium text-white bg-orange-500 rounded-xl hover:bg-orange-600"
            >
              <Menu className="w-4 h-4" />
              Booking List
            </button>
          </div>
        </div>



        {/* Form Content */}
        <Form {...form}>
          <div className="space-y-6">
            
            {/* Hire Slip Date */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="hire_slip_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Hire Slip Date
                    </FormLabel>
                    <FormControl>
                      <Input 
                        type="date" 
                        {...field} 
                        placeholder="Select Hire Slip Date" 
                        readOnly={isReadOnly}
                        className={cn(
                          "h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-900 focus:border-gray-400 dark:focus:border-gray-600 focus:outline-none focus:ring-0",
                          isReadOnly && "bg-gray-50 dark:bg-gray-800 cursor-not-allowed opacity-60"
                        )}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Section Title - Booking Details */}
            <div className="pt-4">
              <h2 className="text-base font-normal text-gray-900 dark:text-gray-100">
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
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Booking No.
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Select Booking No" 
                        readOnly={isReadOnly}
                        className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
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
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Booking Date
                    </FormLabel>
                    <FormControl>
                      <Input 
                        type="date" 
                        {...field} 
                        placeholder="Select Booking Date" 
                        readOnly={isReadOnly}
                        className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
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
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Customer
                    </FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
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
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Company
                    </FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
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
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Destination From
                    </FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
                          <SelectValue placeholder="Select Destination" />
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
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Destination To
                    </FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
                          <SelectValue placeholder="Select Destination" />
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
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Vehicle
                    </FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
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
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Supplier
                    </FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
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
              <h2 className="text-base font-normal text-gray-900 dark:text-gray-100">
                Product / Package Details
              </h2>
            </div>
            
            {/* Product Details Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="product_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Product Name
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Enter Product Name" 
                        readOnly={isReadOnly}
                        className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="no_of_packages"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      No. of Packages
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Enter No. Of Packages" 
                        readOnly={isReadOnly}
                        className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="lr_no"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      LR No.
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Select Your LR No" 
                        readOnly={isReadOnly}
                        className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* LR Date */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="lr_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      LR Date
                    </FormLabel>
                    <FormControl>
                      <Input 
                        type="date" 
                        {...field} 
                        placeholder="Select LR Date" 
                        readOnly={isReadOnly}
                        className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Section Title - Rate / Pricing */}
            <div className="pt-4">
              <h2 className="text-base font-normal text-gray-900 dark:text-gray-100">
                Rate / Pricing
              </h2>
            </div>
            
            {/* First Pricing Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="rate_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Rate Type
                    </FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
                          <SelectValue placeholder="Select Rate Type" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="Fixed">Fixed</SelectItem>
                        <SelectItem value="PerKg">Per Kg</SelectItem>
                        <SelectItem value="PerTon">Per Ton</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="rate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Rate
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Enter Rate" 
                        readOnly={isReadOnly}
                        className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="weight"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Weight
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Enter Weight" 
                        readOnly={isReadOnly}
                        className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Second Pricing Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="freight_amount"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Freight Amount
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Enter Freight Amount" 
                        readOnly={isReadOnly}
                        className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="tds"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      TDS (GST %)
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Enter TDS" 
                        readOnly={isReadOnly}
                        className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="advance"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Advance ₹
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Enter Advance" 
                        readOnly={isReadOnly}
                        className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Balance */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="balance"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Balance (Due ₹)
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Enter Balance" 
                        readOnly={isReadOnly}
                        className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Description */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem className="md:col-span-3">
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Description
                    </FormLabel>
                    <FormControl>
                      <Textarea 
                        {...field} 
                        placeholder="Enter Description" 
                        rows={3} 
                        readOnly={isReadOnly}
                        className="rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
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
                  onClick={handlecancel}
                  className="h-10 px-6 text-sm font-medium text-white bg-gray-900 dark:bg-gray-800 rounded hover:bg-gray-800 dark:hover:bg-gray-700 focus:outline-none"
                >
                  Add Hire Slip
                </Button>
              )}
              
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                className="h-10 px-6 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
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

export default HireSlipForm;