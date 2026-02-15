"use client";
import React, { useEffect, useRef, useState } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, Menu, Trash, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";

const DispatchRowSchema = z.object({
  select: z.boolean().optional(),
  dispatchNoDate: z.string().optional(),
  destinationFromTo: z.string().optional(),
  hireSlipNoDate: z.string().optional(),
  acknowledgementNoDate: z.string().optional(),
  product: z.string().optional(),
  packages: z.string().optional(),
  rateType: z.string().optional(),
  amount: z.string().optional(),
});

const InvoiceSchema = z.object({
  invoicedate: z.string().min(1, "Invoice Date is required"),
  invoiceagainst: z.string().min(1, "Invoice Against is required"),
  customer: z.string().min(1, "Customer is required"),
  company: z.string().min(1, "Company is required"),
  destination_from: z.string().min(1, "Destination From is required"),
  destination_to: z.string().min(1, "Destination To is required"),
  mode: z.enum(["single", "multi"]).default("single"),
  products: z.array(z.object({ productname: z.string().min(1, "Select a product") })),
  dispatch: z.array(DispatchRowSchema),
});

type FormInputs = z.infer<typeof InvoiceSchema>;

type InvoiceFormProps = {
  onClose: () => void;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  invoicedetail?: any;
  mode?: 'add' | 'edit' | 'view';
  readOnly?: boolean;
  asDialog?: boolean;
  onSuccess?: () => void;
};

const InvoiceForm = ({
  onClose,
  open = false,
  onOpenChange,
  invoicedetail,
  mode = "add",
  readOnly = false,
  asDialog = true,
  onSuccess: onSuccessCallback,
}: InvoiceFormProps) => {
  const isInitialized = useRef(false);
  const router = useRouter();
  const [showTable, setShowTable] = useState(true);
  const [selectedProducts, setSelectedProducts] = useState<string[]>([]);

  const form = useForm<FormInputs>({
    resolver: zodResolver(InvoiceSchema),
    defaultValues: {
      invoicedate: "",
      invoiceagainst: "",
      customer: "",
      company: "",
      destination_from: "",
      destination_to: "",
      mode: "single",
      products: [{ productname: "" }],
      dispatch: [
        {
          select: false,
          dispatchNoDate: "",
          destinationFromTo: "",
          hireSlipNoDate: "",
          acknowledgementNoDate: "",
          product: "",
          packages: "",
          rateType: "",
          amount: "",
        },
      ],
    },
  });

  const isReadOnly = readOnly || mode === "view";

  const {
    fields: productFields,
    append: appendProduct,
    remove: removeProduct,
    replace: replaceProducts,
  } = useFieldArray({
    control: form.control,
    name: "products",
  });

  const {
    fields: dispatchFields,
    append: appendDispatch,
    remove: removeDispatch,
    replace: replaceDispatch,
  } = useFieldArray({
    control: form.control,
    name: "dispatch",
  });

  const productOptions = [
    { id: "prod_1", label: "Product A" },
    { id: "prod_2", label: "Product B" },
    { id: "prod_3", label: "Product C" },
  ];

  useEffect(() => {
    if (asDialog) {
      if (open && !isInitialized.current) {
        if (invoicedetail) {
          form.reset({
            ...form.getValues(),
            ...invoicedetail,
            mode: invoicedetail.mode || form.getValues().mode,
            products: invoicedetail.products?.length ? invoicedetail.products : form.getValues().products,
            dispatch: invoicedetail.dispatch?.length ? invoicedetail.dispatch : form.getValues().dispatch,
          });
        }
        isInitialized.current = true;
      } else if (!open) {
        isInitialized.current = false;
      }
    } else {
      if (!isInitialized.current) {
        if (invoicedetail) {
          form.reset(invoicedetail);
        }
        isInitialized.current = true;
      }
    }
  }, [open, invoicedetail?.id]);

  const setMode = (m: "single" | "multi") => {
    form.setValue("mode", m);
    setSelectedProducts([]);
    if (m === "single") {
      replaceProducts([{ productname: "" }]);
      replaceDispatch([
        {
          select: false,
          dispatchNoDate: "",
          destinationFromTo: "",
          hireSlipNoDate: "",
          acknowledgementNoDate: "",
          product: "",
          packages: "",
          rateType: "",
          amount: "",
        },
      ]);
    } else {
      replaceProducts([{ productname: "" }, { productname: "" }]);
      replaceDispatch([
        {
          select: false,
          dispatchNoDate: "",
          destinationFromTo: "",
          hireSlipNoDate: "",
          acknowledgementNoDate: "",
          product: "",
          packages: "",
          rateType: "",
          amount: "",
        },
        {
          select: false,
          dispatchNoDate: "",
          destinationFromTo: "",
          hireSlipNoDate: "",
          acknowledgementNoDate: "",
          product: "",
          packages: "",
          rateType: "",
          amount: "",
        },
      ]);
    }
  };

  const handleClose = () => {
    onOpenChange?.(false);
    form.reset();
    setSelectedProducts([]);
    isInitialized.current = false;
    onClose?.();
  };

  const onSubmit = (values: FormInputs) => {
    console.log("submit", values);
    onSuccessCallback?.();
    handleClose();
  };

  const handleProductSelect = (productId: string) => {
    if (!selectedProducts.includes(productId)) {
      setSelectedProducts([...selectedProducts, productId]);
    }
  };

  const handleProductRemove = (productId: string) => {
    setSelectedProducts(selectedProducts.filter(id => id !== productId));
  };

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950 p-6">
      <div className="w-full px-6 py-4">
        <button
          onClick={handleClose}
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 mb-6 transition-colors text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back</span>
        </button>

        <div className="grid grid-cols-1 md:grid-cols-3 items-center mb-8">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Add Invoice</h1>

          <div className="md:col-start-3 flex justify-end">
            <button type="button" className="flex items-center gap-2 px-3 py-3 text-sm font-medium text-white bg-orange-500 rounded-xl hover:bg-orange-600">
              <Menu className="w-4 h-4" />
              Booking List
            </button>
          </div>
        </div>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <FormField
                  control={form.control}
                  name="invoicedate"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">Invoice Date</FormLabel>
                      <FormControl>
                        <Input
                          type="date"
                          {...field}
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

                <FormField
                  control={form.control}
                  name="invoiceagainst"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">Invoice Against</FormLabel>
                      <FormControl>
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
                      <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">Customer</FormLabel>
                      <FormControl>
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
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <FormField
                  control={form.control}
                  name="company"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">Company</FormLabel>
                      <FormControl>
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
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="destination_from"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">Destination From</FormLabel>
                      <FormControl>
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
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="destination_to"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">Destination To</FormLabel>
                      <FormControl>
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
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Product Details</h1>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="mode"
                    value="single"
                    defaultChecked
                    onChange={() => setMode("single")}
                    disabled={isReadOnly}
                  />
                  Single Product
                </label>

                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="mode"
                    value="multi"
                    onChange={() => setMode("multi")}
                    disabled={isReadOnly}
                  />
                  Multi Products
                </label>
              </div>

              <div className="grid grid-cols-1 gap-4">
                {form.getValues("mode") === "single" ? (
                  productFields.map((p, idx) => (
                    <div key={p.id} className="grid grid-cols-1 md:grid-cols-3 gap-6 items-end">
                      <FormField
                        control={form.control}
                        name={`products.${idx}.productname`}
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                              Product Name
                            </FormLabel>
                            <FormControl>
                              <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                                <FormControl>
                                  <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
                                    <SelectValue placeholder="Select Product" />
                                  </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                  {productOptions.map((opt) => (
                                    <SelectItem key={opt.id} value={opt.id}>
                                      {opt.label}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <div />
                      <div />
                    </div>
                  ))
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div>
                      <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100 mb-2 block">
                        Select Products
                      </FormLabel>
                      <Select onValueChange={handleProductSelect} disabled={isReadOnly}>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-400 dark:text-gray-500">
                          <SelectValue placeholder="Select Products" />
                        </SelectTrigger>
                        <SelectContent>
                          {productOptions.map((opt) => (
                            <SelectItem 
                              key={opt.id} 
                              value={opt.id}
                              disabled={selectedProducts.includes(opt.id)}
                            >
                              {opt.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      
                      {selectedProducts.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-3">
                          {selectedProducts.map((prodId) => {
                            const product = productOptions.find(p => p.id === prodId);
                            return (
                              <div
                                key={prodId}
                                className="flex items-center gap-2 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-3 py-1.5 rounded-md text-sm"
                              >
                                <span>{product?.label}</span>
                                <button
                                  type="button"
                                  onClick={() => handleProductRemove(prodId)}
                                  className="hover:bg-blue-200 dark:hover:bg-blue-800 rounded-full p-0.5"
                                  disabled={isReadOnly}
                                >
                                  <X className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between mt-4">
                <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300">Dispatch Details</h2>
                <button
                  type="button"
                  onClick={() => setShowTable((s) => !s)}
                  className="text-sm text-blue-600 hover:underline"
                >
                  {showTable ? "Hide Table" : "Show Table"}
                </button>
              </div>

              {showTable && (
                <div className="overflow-auto border rounded mt-2">
                  <table className="min-w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="p-2 text-left">Select</th>
                        <th className="p-2 text-left">Dispatch No/Date</th>
                        <th className="p-2 text-left">Destination From & To</th>
                        <th className="p-2 text-left">Hire Slip No/Date</th>
                        <th className="p-2 text-left">Acknowledgement No/Date</th>
                        <th className="p-2 text-left">Product</th>
                        <th className="p-2 text-left">Packages</th>
                        <th className="p-2 text-left">Rate Type</th>
                        <th className="p-2 text-left">Amount</th>
                        {!isReadOnly && <th className="p-2 text-left">Actions</th>}
                      </tr>
                    </thead>

                    <tbody>
                      {dispatchFields.map((d, idx) => (
                        <tr key={d.id} className="border-t">
                          <td className="p-2">
                            <FormField
                              control={form.control}
                              name={`dispatch.${idx}.select`}
                              render={({ field }) => (
                                <FormControl>
                                  <input type="checkbox" checked={!!field.value} onChange={(e) => field.onChange(e.target.checked)} disabled={isReadOnly} />
                                </FormControl>
                              )}
                            />
                          </td>

                          <td className="p-2">
                            <FormField
                              control={form.control}
                              name={`dispatch.${idx}.dispatchNoDate`}
                              render={({ field }) => (
                                <FormControl>
                                  <Input {...field} placeholder="No / Date" readOnly={isReadOnly} className="h-9 text-sm" />
                                </FormControl>
                              )}
                            />
                          </td>

                          <td className="p-2">
                            <FormField
                              control={form.control}
                              name={`dispatch.${idx}.destinationFromTo`}
                              render={({ field }) => (
                                <FormControl>
                                  <Input {...field} placeholder="From - To" readOnly={isReadOnly} className="h-9 text-sm" />
                                </FormControl>
                              )}
                            />
                          </td>

                          <td className="p-2">
                            <FormField
                              control={form.control}
                              name={`dispatch.${idx}.hireSlipNoDate`}
                              render={({ field }) => (
                                <FormControl>
                                  <Input {...field} placeholder="Hire Slip" readOnly={isReadOnly} className="h-9 text-sm" />
                                </FormControl>
                              )}
                            />
                          </td>

                          <td className="p-2">
                            <FormField
                              control={form.control}
                              name={`dispatch.${idx}.acknowledgementNoDate`}
                              render={({ field }) => (
                                <FormControl>
                                  <Input {...field} placeholder="Ack" readOnly={isReadOnly} className="h-9 text-sm" />
                                </FormControl>
                              )}
                            />
                          </td>

                          <td className="p-2">
                            <FormField
                              control={form.control}
                              name={`dispatch.${idx}.product`}
                              render={({ field }) => (
                                <FormControl>
                                  <Select onValueChange={field.onChange} value={field.value} disabled={isReadOnly}>
                                    <FormControl>
                                      <SelectTrigger className="h-9 rounded border border-gray-200 bg-white text-sm">
                                        <SelectValue placeholder="Product" />
                                      </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                      {productOptions.map((opt) => (
                                        <SelectItem key={opt.id} value={opt.id}>
                                          {opt.label}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                </FormControl>
                              )}
                            />
                          </td>

                          <td className="p-2">
                            <FormField
                              control={form.control}
                              name={`dispatch.${idx}.packages`}
                              render={({ field }) => (
                                <FormControl>
                                  <Input {...field} placeholder="Pkgs" readOnly={isReadOnly} className="h-9 text-sm" />
                                </FormControl>
                              )}
                            />
                          </td>

                          <td className="p-2">
                            <FormField
                              control={form.control}
                              name={`dispatch.${idx}.rateType`}
                              render={({ field }) => (
                                <FormControl>
                                  <Input {...field} placeholder="Rate Type" readOnly={isReadOnly} className="h-9 text-sm" />
                                </FormControl>
                              )}
                            />
                          </td>

                          <td className="p-2">
                            <FormField
                              control={form.control}
                              name={`dispatch.${idx}.amount`}
                              render={({ field }) => (
                                <FormControl>
                                  <Input {...field} placeholder="Amount" readOnly={isReadOnly} className="h-9 text-sm" />
                                </FormControl>
                              )}
                            />
                          </td>

                          {!isReadOnly && (
                            <td className="p-2">
                              <div className="flex gap-2">
                                {form.getValues("mode") === "multi" && (
                                  <Button type="button" onClick={() => removeDispatch(idx)} variant="destructive" className="h-8">
                                    <Trash className="w-4 h-4" />
                                  </Button>
                                )}
                              </div>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {form.getValues("mode") === "multi" && !isReadOnly && (
                    <div className="p-3">
                      <Button
                        type="button"
                        onClick={() =>
                          appendDispatch({
                            select: false,
                            dispatchNoDate: "",
                            destinationFromTo: "",
                            hireSlipNoDate: "",
                            acknowledgementNoDate: "",
                            product: "",
                            packages: "",
                            rateType: "",
                            amount: "",
                          })
                        }
                        className="h-10"
                      >
                        <Plus className="w-4 h-4 mr-2" />
                        Add Dispatch Row
                      </Button>
                    </div>
                  )}
                </div>
              )}

              <div className="flex gap-3 pt-6">
                <Button
                  type="submit"
                  className="h-10 px-6 text-sm font-medium text-white bg-gray-900 dark:bg-gray-800 rounded hover:bg-gray-800 dark:hover:bg-gray-700 focus:outline-none"
                  disabled={isReadOnly}
                >
                  Save Invoice
                </Button>

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
          </form>
        </Form>
      </div>
    </div>
  );
}

export default InvoiceForm;