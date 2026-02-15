'use client'
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import React, { useEffect, useState, useRef, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Toast from "@/components/shared/toast";
import { cn } from "@/lib/utils";
import { usePoster, useUpdater } from "@/hooks/use-query";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ChevronDown } from "lucide-react";
import Cookies from "js-cookie";
import { useTranslation } from "@/hooks/use-translations";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

// Define schema for booking
const BookingSchema = z.object({
  bookingDate: z.string().min(1, "Booking date is required"),
  customer: z.string().min(1, "Customer is required"),
  orders: z.array(z.string()).optional(),
  company: z.string().min(1, "Company is required"),
  destinationFrom: z.string().min(1, "Destination from is required"),
  destinationTo: z.string().min(1, "Destination to is required"),
  vehicle: z.string().min(1, "Vehicle is required"),
  supplier: z.string().min(1, "Supplier is required"),
  productName: z.string().min(1, "Product name is required"),
  noOfPackages: z.string().min(1, "Number of packages is required"),
  rateType: z.string().min(1, "Rate type is required"),
  freightAmount: z.string().min(1, "Freight amount is required"),
  weight: z.string().min(1, "Weight is required"),
  rate: z.string().min(1, "Rate is required"),
  cancelDate: z.string().min(1, "Cancel date is required"),
  cancelReason: z.string().min(1, "Cancel reason is required"),
});

type BookingFormProps = {
  booking?: any;
  mode?: 'add' | 'edit' | 'view';
  readOnly?: boolean;
  onSuccess?: () => void;
};

type FormInputs = z.infer<typeof BookingSchema>;

const CancelBooking = ({
  booking,
  mode = 'add',
  readOnly = false,
  onSuccess: onSuccessCallback
}: BookingFormProps) => {

  const { t, isRTL, locale } = useTranslation();
  
  const param = useParams();
  const router = useRouter();
  const isInitialized = useRef(false);
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));

  const form = useForm<FormInputs>({
    resolver: zodResolver(BookingSchema),
    defaultValues: {
      bookingDate: "",
      customer: "",
      orders: undefined,
      company: "",
      destinationFrom: "",
      destinationTo: "",
      vehicle: "",
      supplier: "",
      productName: "",
      noOfPackages: "",
      rateType: "",
      freightAmount: "",
      weight: "",
      rate: "",
    },
  });

  const onSuccess = (response: any) => {
    Toast.fire({
      icon: "success",
      title: mode === 'edit' ? "Booking Updated" : "Booking Added",
    });
    
    router.push("/bookings");
    form.reset();
    isInitialized.current = false;
    
    if (onSuccessCallback) {
      onSuccessCallback();
    }
  };
  
  const onError = (error: any) => {
    console.log(error);
    Toast.fire({
      icon: "error",
      title: error.response?.data?.message || "Submission Failed",
    });
  };

  const addBooking = usePoster("/bookings/add", "booking", onSuccess, onError);
  const updateBooking = useUpdater(`/bookings/update/${booking?.id}`, "bookingbyid", onSuccess, onError);

  const onSubmit = (values: FormInputs) => {
    try {
      console.log(values);
      const currentDate = new Date();
      let data = { ...values };

      if (mode === 'edit' && booking?.id) {
        data = {
          ...data,
        };
        updateBooking.mutate(data);
      } else {
        data = {
          ...data,
        };
        addBooking.mutate(data);
      }
    } catch (error) {
      console.log(error);
    }
  };

  const handleBack = () => {
    router.push("/bookings");
    form.reset();
    isInitialized.current = false;
  };

  const isReadOnly = readOnly || mode === 'view';

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950 p-6" dir={isRTL ? "rtl" : "ltr"}>
      <div className="max-w-7xl mx-auto">
        {/* Back Button */}
        <button
          onClick={handleBack}
          className={cn(
            "flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 mb-6 transition-colors text-sm",
            isRTL && "flex-row-reverse"
          )}
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>

        {/* Heading */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-8">
          Add Booking
        </h1>

          <Button
            type="button"
            variant="outline"
            onClick={handleBack}
            className="h-10 px-6 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
          >
            Order List
          </Button>
          </div>
        {/* Form Content */}
        <Form {...form}>
          <div className="space-y-6">
            
          <FormField
            control={form.control}
            name="orders"
            render={({ field }) => (
              <FormItem>
                <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                  Order
                </FormLabel>

                <FormControl>
                  <Popover>
                    <PopoverTrigger asChild>
                      <button
                        type="button"
                        className="h-11 w-full flex items-center justify-between rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 text-sm text-gray-700 dark:text-gray-300"
                      >
                        {field.value?.length
                          ? field.value.join(", ")
                          : "Select Order"}
                        <ChevronDown className="h-4 w-4 opacity-50" />
                      </button>
                    </PopoverTrigger>

                    <PopoverContent
                      align="start"
                      className="w-[250px] p-3 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded"
                    >
                      {["Order 1", "Order 2", "Order 3"].map((item) => {
                        const isChecked = field.value?.includes(item);

                        return (
                          <label
                            key={item}
                            className="flex items-center gap-2 py-1 cursor-pointer text-sm text-gray-800 dark:text-gray-200"
                          >
                            <input
                              type="checkbox"
                              value={item}
                              checked={isChecked}
                              onChange={(e) => {
                                let updated = field.value ? [...field.value] : [];

                                if (e.target.checked) {
                                  updated.push(item);
                                } else {
                                  updated = updated.filter((v) => v !== item);
                                }

                                field.onChange(updated);
                              }}
                            />
                            {item}
                          </label>
                        );
                      })}
                    </PopoverContent>
                  </Popover>
                </FormControl>

                <FormMessage />
              </FormItem>
            )}
          />



            {/* First Row - Booking Date, Customer, Company */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Booking Date */}
              <FormField
                control={form.control}
                name="bookingDate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Booking Date
                    </FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type="date"
                          {...field}
                          readOnly={isReadOnly}
                          className={cn(
                            "h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-900 focus:border-gray-400 dark:focus:border-gray-600 focus:outline-none focus:ring-0",
                            isReadOnly && "bg-gray-50 dark:bg-gray-800 cursor-not-allowed opacity-60"
                          )}
                        />
                      </div>
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

              {/* Company */}
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
                        <SelectItem value="company1">Company 1</SelectItem>
                        <SelectItem value="company2">Company 2</SelectItem>
                        <SelectItem value="company3">Company 3</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Second Row - Destination From, Destination To, Vehicle */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="destinationFrom"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Destination From
                    </FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
                          <SelectValue placeholder="Select Customer" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="location1">Location 1</SelectItem>
                        <SelectItem value="location2">Location 2</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="destinationTo"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Destination To
                    </FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
                          <SelectValue placeholder="Select Company" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="dest1">Destination 1</SelectItem>
                        <SelectItem value="dest2">Destination 2</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* VEHICLE SOURCE (OWN / HIRE) */}
                <FormField
                  control={form.control}
                  name="vehicle"
                  render={({ field }) => (
                    <FormItem className="md:col-span-3">
                      <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                        Vehicle Source *
                      </FormLabel>

                      <div className="flex items-center gap-6 mt-2">

                        {/* Own Vehicle */}
                        <label className="flex items-center gap-2 text-sm cursor-pointer text-gray-800 dark:text-gray-200">
                          <input
                            type="radio"
                            value="own"
                            checked={field.value === "own"}
                            onChange={() => field.onChange("own")}
                            className="h-4 w-4"
                          />
                          Own Vehicle
                        </label>

                        {/* Hire Vehicle */}
                        <label className="flex items-center gap-2 text-sm cursor-pointer text-gray-800 dark:text-gray-200">
                          <input
                            type="radio"
                            value="hire"
                            checked={field.value === "hire"}
                            onChange={() => field.onChange("hire")}
                            className="h-4 w-4"
                          />
                          Hire Vehicle
                        </label>

                      </div>

                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* VEHICLE DROPDOWN — SHOW ONLY IF HIRE VEHICLE SELECTED */}
                {form.watch("vehicle") === "hire" && (
                  <FormField
                    control={form.control}
                    name="vehicle"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                          Vehicle
                        </FormLabel>
                        <Select onValueChange={field.onChange} value={field.value}>
                          <FormControl>
                            <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
                              <SelectValue placeholder="Select Vehicle" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="vehicle1">Vehicle 1</SelectItem>
                            <SelectItem value="vehicle2">Vehicle 2</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}

            </div>

            {/* Third Row - Supplier */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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
                        <SelectItem value="supplier1">Supplier 1</SelectItem>
                        <SelectItem value="supplier2">Supplier 2</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Section Title */}
             <div className="pt-4">
                          <h2 className="text-base font-normal text-gray-900 dark:text-gray-100">
                            Product / Package Detail
                          </h2>
                        </div>
            
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
                          {/* Product Name */}
                          <FormField
                            control={form.control}
                            name="productName"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                                  Product Name *
                                </FormLabel>
                                <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                                  <FormControl>
                                    <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
                                      <SelectValue placeholder="Select Product" />
                                    </SelectTrigger>
                                  </FormControl>
                                  <SelectContent>
                                    <SelectItem value="product1">Product 1</SelectItem>
                                    <SelectItem value="product2">Product 2</SelectItem>
                                  </SelectContent>
                                </Select>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
            
                          {/* Rate Type */}
                          <FormField
                            control={form.control}
                            name="rateType"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                                  Rate Type *
                                </FormLabel>
                                <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                                  <FormControl>
                                    <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
                                      <SelectValue placeholder="Select Rate Type" />
                                    </SelectTrigger>
                                  </FormControl>
                                  <SelectContent>
                                    <SelectItem value="fixed">Fixed</SelectItem>
                                    <SelectItem value="rtkm">RTKM</SelectItem>
                                    <SelectItem value="perkg">Per KG</SelectItem>
                                  </SelectContent>
                                </Select>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
            
                          {/* No. of Packages */}
                          <FormField
                            control={form.control}
                            name="noOfPackages"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                                  No. of Packages *
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    placeholder="0"
                                    {...field}
                                    className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
            
                          {/* Weight */}
                          <FormField
                            control={form.control}
                            name="weight"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                                  Weight * (In &lt;UOM&gt;)
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    placeholder="Enter Weight"
                                    {...field}
                                    className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                                  />
                                </FormControl>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                  (UOM will auto-load based on selected product)
                                </p>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
            
                          {/* Rate */}
                          <FormField
                            control={form.control}
                            name="rate"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                                  Rate *
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    placeholder="Rate"
                                    {...field}
                                    className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
            
                          {/* KMs */}
                          <FormField
                            control={form.control}
                            name="rate"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                                  Kms
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    placeholder="KMs"
                                    {...field}
                                    className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
            
                          {/* Freight Amount */}
                          <FormField
                            control={form.control}
                            name="freightAmount"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                                  Freight Amt *
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    placeholder="Freight Amount"
                                    {...field}
                                    className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
            
                        </div>
            
                        {/* Remarks */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                          <FormField
                            control={form.control}
                            name="rate"
                            render={({ field }) => (
                              <FormItem className="md:col-span-3">
                                <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                                  Remarks
                                </FormLabel>
                                <FormControl>
                                  <Input
                                    placeholder="Enter Remarks"
                                    {...field}
                                    className="h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        </div>
            
                        {/* Add / Update Product Button */}
                        <div className="flex justify-start">
                          <Button
                            type="button"
                            className="h-10 px-6 bg-teal-600 text-white text-sm font-medium rounded hover:bg-teal-700"
                          >
                            Add / Update Product
                          </Button>
                        </div>
            
            
                        {/* ===================== PRODUCT LIST TABLE ===================== */}
                      <div className="mt-10 border rounded-lg overflow-hidden">
            
                        {/* Header */}
                        <div className="grid grid-cols-8 bg-gray-200 dark:bg-gray-800 text-xs font-semibold text-gray-700 dark:text-gray-100">
                          <div className="p-2 border">Product Name</div>
                          <div className="p-2 border">No. of Packages</div>
                          <div className="p-2 border">Weight (In &lt;UOM&gt;)</div>
                          <div className="p-2 border">Rate Type</div>
                          <div className="p-2 border">Rate</div>
                          <div className="p-2 border">Kms</div>
                          <div className="p-2 border">Freight Amt</div>
                          <div className="p-2 border">Remarks</div>
                        </div>
            
                        {/* Empty Row */}
                        <div className="grid grid-cols-8 text-sm">
                          <div className="p-3 border"></div>
                          <div className="p-3 border"></div>
                          <div className="p-3 border"></div>
                          <div className="p-3 border"></div>
                          <div className="p-3 border"></div>
                          <div className="p-3 border"></div>
                          <div className="p-3 border"></div>
                          <div className="p-3 border"></div>
                        </div>
            
                        {/* Total Freight Row */}
                        <div className="grid grid-cols-8 text-sm bg-gray-100 dark:bg-gray-900">
                          <div className="p-3 border col-span-5"></div>
                          <div className="p-3 border text-center font-medium">Total</div>
                          <div className="p-3 border font-medium">Total Freight Amt</div>
                          <div className="p-3 border"></div>
                        </div>
            
                        {/* Description */}
                        <div className="grid grid-cols-8">
                          <div className="border p-2 font-medium text-sm">
                            Description<span className="text-red-500">*</span>
                          </div>
                          <div className="border p-2 col-span-7">
                            <textarea
                              className="w-full h-20 text-sm p-2 border rounded bg-white dark:bg-gray-900"
                              placeholder="Enter Description"
                            ></textarea>
                          </div>
                        </div>
                      </div>
                      {/* ===================== END PRODUCT LIST TABLE ===================== */}
            
            <div className="pt-4">
                        <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                          Cancel Details
                        </h2>
                      </div>
            
                      {/* Cancel Date and Remark */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <FormField
                          control={form.control}
                          name="cancelDate"
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
                          name="cancelReason"
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

                        {/* Action Buttons */}
                        <div className={cn("flex gap-3 pt-6", isRTL && "flex-row-reverse")}>
                          {!isReadOnly && (
                            <Button
                              type="button"
                              onClick={form.handleSubmit(onSubmit)}
                              disabled={addBooking.isLoading || updateBooking.isLoading}
                              className="h-10 px-6 text-sm font-medium text-white bg-gray-900 dark:bg-gray-800 rounded hover:bg-gray-800 dark:hover:bg-gray-700 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {addBooking.isLoading || updateBooking.isLoading ? "Saving..." : "Save"}
                            </Button>
                          )}
            
                          <Button
                            type="button"
                            variant="outline"
                            onClick={handleBack}
                            className="h-10 px-6 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
                          >
                            Close
                          </Button>
                        </div>
                        </div>
          </div>
        </Form>
      </div>
    </div>
  );
};

export default CancelBooking;