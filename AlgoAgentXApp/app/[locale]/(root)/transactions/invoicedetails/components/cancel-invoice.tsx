'use client'
import React, { useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { cn } from "@/lib/utils";

// Define the schema for Cancel Invoice
const CancelInvoiceSchema = z.object({
  invoice_no: z.string().min(1, "Invoice No is required"),
  invoicedate: z.string().min(1, "Invoice Date is required"),
  status: z.string().optional(),
  invoiceagainst: z.string().optional(),
  invoice_amount: z.string().optional(),
  customer: z.string().optional(),
  destination_from: z.string().optional(),
  product_name: z.string().optional(),
  description: z.string().optional(),
  cancel_date: z.string().min(1, "Cancel Date is required"),
  cancel_remark: z.string().min(1, "Cancel Remark is required"),
});

type FormInputs = z.infer<typeof CancelInvoiceSchema>;

type CancelInvoiceFormProps = {
  onClose: () => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  invoiceData?: any;
  mode?: 'add' | 'edit' | 'view';
  readOnly?: boolean;
  asDialog?: boolean;
  onSuccess?: () => void;
};

const CancelInvoice = ({
  onClose,
  open = false,
  onOpenChange,
  invoiceData,
  mode = 'add',
  readOnly = false,
  asDialog = true,
  onSuccess: onSuccessCallback
}: CancelInvoiceFormProps) => {

  const form = useForm<FormInputs>({
    resolver: zodResolver(CancelInvoiceSchema),
    defaultValues: invoiceData || {
      invoice_no: "",
      invoicedate: "",
      status: "",
      invoiceagainst: "",
      invoice_amount: "",
      customer: "",
      destination_from: "",
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
      <div className="max-w-7xl mx-auto">
        {/* Back Button */}
        <button
          onClick={() => onClose?.()}
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 mb-6 transition-colors text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>

        {/* Heading */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Invoice Cancel
          </h1>
          <button
            onClick={() => onClose?.()}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Content */}
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          
            {/* Section Title - Invoice Details */}
            <div>
              <h2 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-4">
                Invoice Details
              </h2>
            </div>
          
            {/* First Row - Invoice No, Invoice Date, Status */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="invoice_no"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                      Invoice No.
                    </FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                      <FormControl>
                        <SelectTrigger className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
                          <SelectValue placeholder="Select Invoice No." />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {/* Options will be populated from API */}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="invoicedate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                      Invoice Date
                    </FormLabel>
                    <FormControl>
                      <Input 
                        type="date" 
                        {...field} 
                        placeholder="Select Invoice Date" 
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
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Status" 
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
            </div>

            {/* Second Row - Invoice For, Invoice Amount, Customer */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="invoiceagainst"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                      Invoice For
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Invoice For" 
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
                name="invoice_amount"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                      Invoice Amount
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Invoice Amount" 
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
                name="customer"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                      Customer
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Customer" 
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
            </div>

            {/* Third Row - Destination From */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="destination_from"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                      Destination From
                    </FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        placeholder="Destination From" 
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
            </div>

            {/* Section Title - Product Details */}
            <div className="pt-4">
              <h2 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-4">
                Product Details
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
                        placeholder="Product Name" 
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
                        placeholder="Description" 
                        rows={3} 
                        readOnly={isReadOnly}
                        className={cn(
                          "rounded-lg border border-gray-300 dark:border-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-900",
                          isReadOnly && "bg-gray-50 dark:bg-gray-800 cursor-not-allowed opacity-60"
                        )}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Section Title - Cancel Details */}
            <div className="pt-4">
              <h2 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-4">
                Cancel Details
              </h2>
            </div>

            {/* Cancel Date and Cancel Remark */}
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
                        placeholder="Select Cancel Date" 
                        readOnly={isReadOnly}
                        className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 px-3 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-900"
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
                        placeholder="Enter Cancel Remark" 
                        readOnly={isReadOnly}
                        className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 px-3 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-900"
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
                  type="submit"
                  className="h-10 px-6 text-sm font-medium text-white bg-gray-900 dark:bg-gray-800 rounded-lg hover:bg-gray-800 dark:hover:bg-gray-700 focus:outline-none"
                >
                  Cancel Invoice
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
          </form>
        </Form>
      </div>
    </div>
  );
};

export default CancelInvoice;