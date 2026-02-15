"use client";

import FormFooter from "@/components/shared/form-footer";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import Toast from "@/components/shared/toast";
import { cn } from "@/lib/utils";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { useFetcher, usePoster, useUpdater } from "@/hooks/use-query";
import Cookies from "js-cookie";
import { Order } from "@/types/order-type";
import { OrderSchema } from "@/schemas/order-schema";
import { useTranslation } from "@/hooks/use-translations";
import z from "zod";
import axios from "axios";
import { AnyARecord } from "node:dns";
import { useWatch } from "react-hook-form";

type OrderProductFormProps = {
  mode?: "add" | "edit" | "view";
  order?: Order;
  readOnly?: boolean;
  onSuccess?: () => void;
};

type FormInputs = z.infer<typeof OrderSchema>;

const OrderproductForm = ({
  mode,
  order,
  readOnly,
  onSuccess: onSuccessCallback,
}: OrderProductFormProps) => {
  const router = useRouter();
  const isInitialized = useRef(false);
  const param = useParams();
  const { t, isRTL } = useTranslation();

  const [selectedCustomer, setSelectedCustomer] = useState("");
  const [selectedFromDestination, setSelectedFromDestination] = useState("");
  const [selectedToDestination, setSelectedToDestination] = useState("");

  const loggedinuserid = Cookies.get("loggedinuserid");

  // Auto-determine mode if not provided
  const effectiveMode = mode || (param["id"] ? "edit" : "add");

  const form = useForm<FormInputs>({
    resolver: zodResolver(OrderSchema),
    defaultValues: order ?? {
      order_no: "",
      order_date: undefined,
      order_source: "",
      customer_id: "",
      company_id: "",
      from_destination_id: 0,
      to_destination_id: 0,
      dispatch_from: undefined,
      dispatch_to: undefined,
      vehicle_source: "",
      kms: undefined,
      status: "",
      created_by: undefined,
      products: [
        {
          product_id: 0,
          no_of_packages: 0,
          weight: 0,
          rate_type: "",
          rate_type_id: 0, 
          rate: 0,
          kms: 0,
          fright_amount: 0,
          remarks: "",
        },
      ],
    },
  });

  // 🔥 FIX 1: Consolidate form initialization into ONE effect with guard
  useEffect(() => {
    if (order && !isInitialized.current) {
      form.reset(order);

      // Initialize state from order data
      if (order.customer_id) setSelectedCustomer(String(order.customer_id));
      if (order.from_destination_id)
        setSelectedFromDestination(String(order.from_destination_id));
      if (order.to_destination_id)
        setSelectedToDestination(String(order.to_destination_id));

      isInitialized.current = true;
    }
  }, [order, form]);

  const { control, register } = form;

  const { fields, append, remove } = useFieldArray({
    control,
    name: "products",
  });

  const onSuccess = () => {
    Toast.fire({
      icon: "success",
      title: param["id"]
        ? "Order Updated Successfully"
        : "Order Added Successfully",
    });

    router.push("/transactions");

    if (onSuccessCallback) onSuccessCallback();
  };

  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e?.response?.data?.message || "Something Went Wrong",
    });
  };

  const addOrder = usePoster("/order/add", "order", onSuccess, onError);
  const updateOrder = useUpdater(
    `/order/update/${param["id"] || ""}`,
    "orderbyid",
    onSuccess,
    onError
  );

  const { data: productfectchdetails } = useFetcher(
    `order/get-products-rates/`,
    "orderproductsdetails"
  );

  const { data: customerList } = useFetcher(
    `order/customer/`,
    "customer/dropdown"
  );
  const { data: companyList } = useFetcher(
    `order/company/`,
    "company/dropdown"
  );
  const { data: destinationList } = useFetcher(
    `order/destination/`,
    "destination/dropdown"
  );

  const getOrderSourceOptions = () => {
    return ["Whatsapp", "Email", "Call"];
  };

  const orderDate = form.watch("order_date");

  // ✅ Fetch products list with unique key
  const {
    data: productsRates,
    refetch: refetchProducts,
    isLoading: isProductsLoading,
  } = useFetcher(
    `/order/get-products-rates?customer_id=${selectedCustomer}&from_destination_id=${selectedFromDestination}&to_destination_id=${selectedToDestination}&order_date=${orderDate}`,
    "ProductsRatesList",
    false
  );

  // ✅ Watch all product IDs and create comma-separated query
  const selectedProductIds =
    form
      .watch("products")
      ?.map((p) => p?.product_id)
      .filter((id): id is number => id !== undefined && id > 0) || [];

  const query = selectedProductIds.join(",");

  const { data: Rates, refetch: refetchRates } = useFetcher(
    query
      ? `/order/get-rate-details?product_id=${query}&order_date=${orderDate}`
      : "",
    "ProductRateDetails",
    false
  );

  const uniqueProducts = useMemo(() => {
    if (!productsRates) return [];

    return Array.from(
      new Map(productsRates.map((p: any) => [p.product_id, p])).values()
    );
  }, [productsRates]);

  // Fetch products when customer/destinations change
  useEffect(() => {
    if (
      selectedCustomer &&
      selectedFromDestination &&
      selectedToDestination &&
      orderDate
    ) {
      refetchProducts();
    }
  }, [
    selectedCustomer,
    selectedFromDestination,
    selectedToDestination,
    orderDate,
    refetchProducts,
  ]);

  // Fetch rates when product IDs change
  useEffect(() => {
    if (query) {
      refetchRates();
    }
  }, [query, refetchRates]);

  // 🔥 FIX 2: Use a ref to prevent infinite loops when updating rates
  const lastRatesUpdateRef = useRef<string>("");

 useEffect(() => {
  if (!Rates) return;

  const ratesSignature = JSON.stringify(Rates);
  if (lastRatesUpdateRef.current === ratesSignature) return;
  lastRatesUpdateRef.current = ratesSignature;

  fields.forEach((_, index) => {
    const productId = form.getValues(`products.${index}.product_id`);
    if (!productId) return;

    const match = Rates.find((r: any) => r.product_id === productId);
    if (!match) return;

    // Set rate and kms
    form.setValue(`products.${index}.rate`, match.rate);
    form.setValue(`products.${index}.kms`, match.billing_kms);

    // Display string for user
    form.setValue(`products.${index}.rate_type`, match.rate_type, {
      shouldDirty: false,
      shouldValidate: false,
    });

    // Backend ID for submission
    form.setValue(`products.${index}.rate_type_id`, match.rate_type_id, {
      shouldDirty: false,
      shouldValidate: false,
    });
  });
}, [Rates, fields, form]);


const onSubmit = (values: FormInputs) => {
  const userId = loggedinuserid ? Number(loggedinuserid) : undefined;

  const payload = {
    ...values,
    customer_id: values.customer_id ? Number(values.customer_id) : undefined,
    company_id: values.company_id ? Number(values.company_id) : undefined,
    products: values.products.map((p) => ({
      ...p,
      product_id: Number(p.product_id),
      rate_type_id: Number(p.rate_type_id), // send ID to backend
      // keep rate_type as string for display & validation
      rate_type: p.rate_type || "",
      no_of_packages: Number(p.no_of_packages),
      weight: Number(p.weight),
      rate: Number(p.rate),
      kms: Number(p.kms),
      fright_amount: Number(p.fright_amount),
    })),
  };

  if (param["id"]) {
    updateOrder.mutate({
      ...payload,
      updated_by: userId,
      updated_on: new Date(),
    });
  } else {
    addOrder.mutate({
      ...payload,
      status: "Pending",
      created_by: userId,
      created_on: new Date(),
    });
  }
};



  const handleBack = () => {
    router.push("/transactions");
    form.reset();
    isInitialized.current = false;
  };

  const watchedProducts = useWatch({
    control: form.control,
    name: "products",
  });

  // 🔥 FIX 3: Use ref to track last calculated values
  // 🔥 FIX 3 (UPDATED): Rate-type based freight calculation
  const lastFreightCalculation = useRef<Map<number, number>>(new Map());

  useEffect(() => {
  watchedProducts?.forEach((product, index) => {
    // Make sure rate_type is a string
    const rateType = (product?.rate_type || "").toLowerCase();
    const rate = Number(product?.rate) || 0;
    const weight = Number(product?.weight) || 0;
    const packages = Number(product?.no_of_packages) || 0;

    let freightAmount = 0;

    if (rateType === "per pg") {
      freightAmount = packages * rate;
    } else if (rateType === "per kg") {
      freightAmount = (weight / 1000) * rate;
    } else if (rateType === "per ton") {
      freightAmount = weight * rate;
    }

    freightAmount = Number(freightAmount.toFixed(2));

    const lastValue = lastFreightCalculation.current.get(index);
    if (lastValue !== freightAmount) {
      lastFreightCalculation.current.set(index, freightAmount);

      const currentFreight = form.getValues(`products.${index}.fright_amount`);
      if (currentFreight !== freightAmount) {
        form.setValue(`products.${index}.fright_amount`, freightAmount, {
          shouldDirty: true,
          shouldValidate: false,
        });
      }
    }
  });
}, [watchedProducts, form]);


  // 🔥 FIX 4: Simplify the zero freight amount effect
  useEffect(() => {
    watchedProducts?.forEach((p, index) => {
      if (!p?.product_id || p.product_id === 0) {
        const currentFreight = form.getValues(
          `products.${index}.fright_amount`
        );
        if (currentFreight !== 0) {
          form.setValue(`products.${index}.fright_amount`, 0, {
            shouldDirty: false,
            shouldValidate: false,
          });
        }
      }
    });
  }, [watchedProducts, form]);

  return (
    <div
      className="min-h-screen bg-white dark:bg-gray-950 p-6"
      dir={isRTL ? "rtl" : "ltr"}
    >
      <div className="max-w-7xl mx-auto">
        
      <Form {...form}>
          <div className="space-y-6">
            {/* First Row - Booking Date, Customer, Company */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Booking Date */}
              <FormField
                control={form.control}
                name="order_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Order Date <span className="text-red-500">*</span>
                    </FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type="date"
                          {...field}
                          value={
                            field.value
                              ? new Date(field.value)
                                  .toISOString()
                                  .split("T")[0]
                              : ""
                          }
                          onChange={(e) => {
                            const date = e.target.value
                              ? new Date(e.target.value)
                              : undefined;
                            field.onChange(date);
                          }}
                          disabled={readOnly}
                          className={cn(
                            "h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-900 focus:border-gray-400 dark:focus:border-gray-600 focus:outline-none focus:ring-0",
                            readOnly &&
                              "bg-gray-50 dark:bg-gray-800 cursor-not-allowed opacity-60"
                          )}
                        />
                      </div>
                    </FormControl>
                    <FormMessage>
                      {form.formState.errors.order_date?.message}
                    </FormMessage>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="order_no"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Order No.
                    </FormLabel>

                    <FormControl>
                      <Input
                        {...field}
                        placeholder="Enter Order No."
                        disabled={readOnly}
                        className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                      />
                    </FormControl>

                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="order_source"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Order Source <span className="text-red-500">*</span>
                    </FormLabel>

                    <Select
                      onValueChange={field.onChange}
                      value={field.value ?? ""} // default to empty string
                      disabled={readOnly}
                    >
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
                          <SelectValue placeholder="Select Order Source" />
                        </SelectTrigger>
                      </FormControl>

                      <SelectContent>
                        {getOrderSourceOptions().map((item) => (
                          <SelectItem key={item} value={item}>
                            {item}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <FormMessage>
                      {form.formState.errors.order_source?.message}
                    </FormMessage>
                  </FormItem>
                )}
              />

              {/* Customer */}
              <FormField
                control={form.control}
                name="customer_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Customer <span className="text-red-500">*</span>
                    </FormLabel>

                    <Select
                      onValueChange={(value) => {
                        field.onChange(value);
                        setSelectedCustomer(value); // ⬅ update Customer state
                      }}
                      value={field.value ? String(field.value) : ""}
                      disabled={readOnly}
                    >
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900">
                          <SelectValue placeholder="Select Customer" />
                        </SelectTrigger>
                      </FormControl>

                      <SelectContent>
                        {customerList?.map((item: any) => (
                          <SelectItem
                            key={item.customer_id}
                            value={String(item.customer_id)}
                          >
                            {item.customer_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Company */}
              <FormField
                control={form.control}
                name="company_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Company <span className="text-red-500">*</span>
                    </FormLabel>

                    <Select
                      onValueChange={field.onChange}
                      value={field.value ? String(field.value) : ""}
                      disabled={readOnly}
                    >
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
                          <SelectValue placeholder="Select Company" />
                        </SelectTrigger>
                      </FormControl>

                      <SelectContent>
                        {companyList?.map((item: any) => (
                          <SelectItem
                            key={item.company_id}
                            value={String(item.company_id)}
                          >
                            {item.company_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <FormMessage>
                      {form.formState.errors.company_id?.message}
                    </FormMessage>
                  </FormItem>
                )}
              />

              {/* Second Row - Destination From, Destination To, Vehicle */}

              <FormField
                control={form.control}
                name="from_destination_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Destination From <span className="text-red-500">*</span>
                    </FormLabel>

                    <Select
                      onValueChange={(value) => {
                        field.onChange(value);
                        setSelectedFromDestination(value); // ⬅ update FROM state
                      }}
                      value={field.value ? String(field.value) : ""}
                      disabled={readOnly}
                    >
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900">
                          <SelectValue placeholder="Select Destination From" />
                        </SelectTrigger>
                      </FormControl>

                      <SelectContent>
                        {destinationList?.map((item: any) => (
                          <SelectItem
                            key={item.destination_id}
                            value={String(item.destination_id)}
                          >
                            {item.destination}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="to_destination_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Destination To <span className="text-red-500">*</span>
                    </FormLabel>

                    <Select
                      onValueChange={(value) => {
                        field.onChange(value);
                        setSelectedToDestination(value); // ⬅ update TO state
                      }}
                      value={field.value ? String(field.value) : ""}
                      disabled={readOnly}
                    >
                      <FormControl>
                        <SelectTrigger className="h-11 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900">
                          <SelectValue placeholder="Select Destination To" />
                        </SelectTrigger>
                      </FormControl>

                      <SelectContent>
                        {destinationList?.map((item: any) => (
                          <SelectItem
                            key={item.destination_id}
                            value={String(item.destination_id)}
                          >
                            {item.destination}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <FormField
                  control={form.control}
                  name="vehicle_source"
                  render={({ field }) => (
                    <FormItem className="md:col-span-3">
                      <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                        Vehicle Source *
                      </FormLabel>

                      <div className="flex items-center gap-6 mt-2">
                        <label className="flex items-center gap-2 text-sm cursor-pointer text-gray-800 dark:text-gray-200">
                          <input
                            type="radio"
                            value="own"
                            disabled={readOnly}
                            checked={field.value === "own"}
                            onChange={field.onChange}
                            className="h-4 w-4"
                          />
                          Own Vehicle
                        </label>

                        <label className="flex items-center gap-2 text-sm cursor-pointer text-gray-800 dark:text-gray-200">
                          <input
                            type="radio"
                            value="hire"
                            disabled={readOnly}
                            checked={field.value === "hire"}
                            onChange={field.onChange}
                            className="h-4 w-4"
                          />
                          Hire Vehicle
                        </label>
                      </div>

                      <FormMessage>
                        {form.formState.errors.vehicle_source?.message}
                      </FormMessage>
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="dispatch_from"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Dispatch From <span className="text-red-500">*</span>
                    </FormLabel>

                    <FormControl>
                      <div className="relative">
                        <Input
                          type="date"
                          {...field}
                          value={
                            field.value
                              ? new Date(field.value)
                                  .toISOString()
                                  .split("T")[0]
                              : ""
                          }
                          onChange={(e) => {
                            const date = e.target.value
                              ? new Date(e.target.value)
                              : "";
                            field.onChange(date);
                          }}
                          disabled={readOnly}
                          className={cn(
                            "h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-900 focus:border-gray-400 dark:focus:border-gray-600 focus:outline-none focus:ring-0",
                            readOnly &&
                              "bg-gray-50 dark:bg-gray-800 cursor-not-allowed opacity-60"
                          )}
                        />
                      </div>
                    </FormControl>

                    <FormMessage>
                      {form.formState.errors.dispatch_from?.message}
                    </FormMessage>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="dispatch_to"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-normal text-gray-900 dark:text-gray-100">
                      Dispatch To <span className="text-red-500">*</span>
                    </FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Input
                          type="date"
                          {...field}
                          value={
                            field.value
                              ? new Date(field.value)
                                  .toISOString()
                                  .split("T")[0]
                              : ""
                          }
                          onChange={(e) => {
                            const date = e.target.value
                              ? new Date(e.target.value)
                              : "";
                            field.onChange(date);
                          }}
                          disabled={readOnly}
                          className={cn(
                            "h-11 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-900 focus:border-gray-400 dark:focus:border-gray-600 focus:outline-none focus:ring-0",
                            readOnly &&
                              "bg-gray-50 dark:bg-gray-800 cursor-not-allowed opacity-60"
                          )}
                        />
                      </div>
                    </FormControl>

                    <FormMessage>
                      {form.formState.errors.dispatch_to?.message}
                    </FormMessage>
                  </FormItem>
                )}
              />
            </div>

            {/* ================= PRODUCT / PACKAGE DETAIL MISSING FIELDS ================= */}
            {/* PRODUCT / PACKAGE DETAILS  */}
            <div className="mt-8 w-full">
              {/* Title */}
              <div className="font-semibold mb-3 bg-gray-100 border border-gray-300 px-6 py-2 rounded">
                Product / Package Details
              </div>

              {/* Bordered Container */}
              <div className="w-full py-4 border border-gray-300 rounded-lg p-4">
                {/* Header Row */}
                <div className="grid grid-cols-[60px_1fr_1fr_1fr_1fr_1fr_1fr_1fr_1fr_40px] gap-4 text-sm font-medium text-gray-700 pb-2 px-1">
                  <div>Item No.</div>
                  <div>
                    Product Name <span className="text-red-500">*</span>
                  </div>
                  <div>
                    No. of Packages <span className="text-red-500">*</span>
                  </div>
                  <div>
                    Weight <span className="text-red-500">*</span>
                  </div>
                  <div>
                    Rate Type <span className="text-red-500">*</span>
                  </div>
                  <div>
                    Rate <span className="text-red-500">*</span>
                  </div>
                  <div>
                    KMs <span className="text-red-500">*</span>
                  </div>
                  <div>
                    Freight Amt <span className="text-red-500">*</span>
                  </div>
                  <div>
                    Remarks <span className="text-red-500">*</span>
                  </div>
                  <div></div>
                </div>

                {/* Dynamic Rows */}
                {fields.map((row, index) => (
                  <div
                    key={row.id}
                    className="grid grid-cols-[60px_1fr_1fr_1fr_1fr_1fr_1fr_1fr_1fr_40px] gap-4 mb-3 items-center px-1"
                  >
                    {/* Item No */}
                    <div className="text-gray-700">{index + 1}</div>

                    {/* Product Name */}
                    <FormField
                      control={form.control}
                      name={`products.${index}.product_id`}
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Select
                              value={
                                field.value === 0 ? "" : String(field.value)
                              }
                              onValueChange={(val) =>
                                field.onChange(Number(val))
                              }
                            >
                              <SelectTrigger className="h-10">
                                <SelectValue placeholder="Select" />
                              </SelectTrigger>

                              <SelectContent>
                                {uniqueProducts.length > 0 ? (
                                  uniqueProducts.map((p: any) => (
                                    <SelectItem
                                      key={p.product_id}
                                      value={String(p.product_id)}
                                    >
                                      {p.product_name}
                                    </SelectItem>
                                  ))
                                ) : (
                                  <div className="p-2 text-gray-400 text-sm">
                                    No applicable products
                                  </div>
                                )}
                              </SelectContent>
                            </Select>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {/* No. of Packages */}
                    <FormField
                      control={form.control}
                      name={`products.${index}.no_of_packages`}
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Input
                              {...field}
                              placeholder="0"
                              className="h-10"
                              readOnly={readOnly}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {/* Weight */}
                    <FormField
                      control={form.control}
                      name={`products.${index}.weight`}
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Input
                              {...field}
                              placeholder="0"
                              className="h-10"
                              readOnly={readOnly}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {/* Rate Type */}
                    <FormField
                      control={form.control}
                      name={`products.${index}.rate_type`}
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Input
                              {...field}
                              placeholder="Enter Rate Type"
                              className="h-10"
                              readOnly
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />

                    {/* Rate */}
                    <FormField
                      control={form.control}
                      name={`products.${index}.rate`}
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Input {...field} className="h-10" readOnly />
                          </FormControl>
                        </FormItem>
                      )}
                    />

                    {/* KMs */}
                    <FormField
                      control={form.control}
                      name={`products.${index}.kms`}
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Input {...field} className="h-10" readOnly />
                          </FormControl>
                        </FormItem>
                      )}
                    />

                    {/* Freight Amount */}
                    <FormField
                      control={form.control}
                      name={`products.${index}.fright_amount`}
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Input
                              {...field}
                              placeholder="0"
                              className="h-10"
                              readOnly={readOnly}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {/* Remarks */}
                    <FormField
                      control={form.control}
                      name={`products.${index}.remarks`}
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <Input
                              {...field}
                              placeholder="Remarks"
                              className="h-10"
                              readOnly={readOnly}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {/* Delete */}
                    <div className="flex items-center">
                      {!readOnly && index > 0 && (
                        <button
                          type="button"
                          onClick={() => remove(index)}
                          className="text-red-500 font-semibold text-lg"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  </div>
                ))}

                {/* Add Button */}
                {!readOnly && (
                  <button
                    type="button"
                    onClick={() =>
                      append({
                        product_id: 0,
                        no_of_packages: 0,
                        weight: 0,
                        rate_type: "",
                        rate: 0,
                        kms: 0,
                        fright_amount: 0,
                        remarks: "",
                      })
                    }
                    className="text-blue-600 font-medium mt-2 px-1"
                  >
                    + Add
                  </button>
                )}
              </div>
            </div>

            {/* ===================== END PRODUCT LIST TABLE ===================== */}

            {/* Action Buttons */}
            <div className={cn("flex gap-3 pt-6", isRTL && "flex-row-reverse")}>
              {!readOnly && (
                <Button
                  type="button"
                  onClick={form.handleSubmit(onSubmit)}
                  disabled={addOrder.isLoading || updateOrder.isLoading}
                  className="h-10 px-6 text-sm font-medium text-white bg-gray-900 dark:bg-gray-800 rounded hover:bg-gray-800 dark:hover:bg-gray-700 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {addOrder.isLoading || updateOrder.isLoading
                    ? "Saving..."
                    : "Save"}
                </Button>
              )}

              <Button
                type="button"
                variant="outline"
                onClick={handleBack}
                className="h-10 px-6 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                Cancel
              </Button>
            </div>
          </div>
        </Form>
      </div>
    </div>
  );
};

export default OrderproductForm;
