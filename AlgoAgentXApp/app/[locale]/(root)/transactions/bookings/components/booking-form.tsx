"use client";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import React, { useEffect, useState, useRef, useMemo } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Toast from "@/components/shared/toast";
import { cn } from "@/lib/utils";
import { useFetcher, usePoster, useUpdater } from "@/hooks/use-query";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Cookies from "js-cookie";
import { useTranslation } from "@/hooks/use-translations";
import { MultiSelectPopup } from "./order-popup";
import { BookingSchema } from "@/schemas/booking-schema";
import { Booking } from "@/types/booking.type";

type BookingFormProps = {
  booking?: Booking;
  mode?: "add" | "edit" | "view";
  readOnly?: boolean;
  onSuccess?: () => void;
};

type FormInputs = z.infer<typeof BookingSchema>;

const BookingForm = ({
  booking,
  mode = "add",
  readOnly = false,
  onSuccess: onSuccessCallback,
}: BookingFormProps) => {
  const { t, isRTL, locale } = useTranslation();

  const param = useParams();
  const router = useRouter();
  const isInitialized = useRef(false);
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));
  const [openOrderPopup, setOpenOrderPopup] = useState(false);
  const [initialCompanyId, setInitialCompanyId] = useState<number | undefined>(
    undefined
  );
  const [initialCustomerId, setInitialCustomerId] = useState<
    number | undefined
  >(undefined);

  const form = useForm<FormInputs>({
    resolver: zodResolver(BookingSchema),
    defaultValues: {
      booking_id: undefined,
      booking_no: "",
      booking_date: "",
      customer_id: undefined,
      company_id: undefined,
      order_no: [],
      vehicle_id: undefined,
      from_destination_id: undefined,
      to_destination_id: undefined,
      supplier_id: undefined,
      vehicle_source_booking: "own",
      status: "ACTIVE",
      created_by: 1,
      created_on: undefined,
      modified_by: undefined,
      modified_on: undefined,
      status_updatedby: undefined,
      status_updatedon: undefined,
      products: [
        {
          booking_product_id: undefined,
          booking_item_no: undefined,
          product_id: null,
          no_of_packages: undefined,
          weight: undefined,
          rate: undefined,
          rate_type_id: null,
          kms: undefined,
          fright_amount: undefined,
          remarks: "",
          booking_id: undefined,
          order_id: undefined,
        },
      ],
    },
  });

  const { control, register } = form;

  const { fields, append, remove, replace } = useFieldArray({
    control,
    name: "products",
  });

  const onSuccess = (response: any) => {
    Toast.fire({
      icon: "success",
      title: mode === "edit" ? "Booking Updated" : "Booking Added",
    });

    router.push("/transactions");
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

  const addBooking = usePoster(
    "/transaction/booking/add",
    "booking",
    onSuccess,
    onError
  );
  const updateBooking = useUpdater(
    `/transaction/booking/update/${booking?.booking_id}`,
    "bookingbyid",
    onSuccess,
    onError
  );

  const onSubmit = (values: FormInputs) => {
    try {
      console.log("🔥 RAW FORM VALUES:", values);

      const selectedOrders = values.order_no || [];

      // Validate orders for ADD mode only
      if (mode === "add" && selectedOrders.length === 0) {
        Toast.fire({
          icon: "error",
          title: "Please select at least one order",
        });
        return;
      }

      // Prepare order_no (CSV string or existing)
      const orderNoCSV =
        selectedOrders.length > 0
          ? selectedOrders.map((o) => o.name).join(",")
          : booking?.order_no || "";

      // Get destinations from orders or form values
      const fromDest =
        selectedOrders.length > 0
          ? selectedOrders[0]?.raw?.from_destination_id
          : values.from_destination_id;

      const toDest =
        selectedOrders.length > 0
          ? selectedOrders[0]?.raw?.to_destination_id
          : values.to_destination_id;

      // ✅ Prepare products - Keep booking_product_id for updates
      const products = values.products.map((p, index) => ({
        booking_product_id: p.booking_product_id
          ? Number(p.booking_product_id)
          : undefined,
        order_id: p.order_id ? Number(p.order_id) : undefined,
        booking_item_no: p.booking_item_no ?? index + 1,
        product_id: p.product_id,
        no_of_packages: p.no_of_packages,
        weight: p.weight,
        rate: p.rate,
        rate_type_id: p.rate_type_id,
        kms: p.kms,
        fright_amount: p.fright_amount,
        remarks: p.remarks,
      }));

      // Simple data object
      const data = {
        booking_no: values.booking_no || "",
        booking_date:
          values.booking_date || new Date().toISOString().split("T")[0],
        customer_id: values.customer_id,
        company_id: values.company_id,
        order_no: orderNoCSV,
        vehicle_id: values.vehicle_id,
        from_destination_id: fromDest || null,
        to_destination_id: toDest || null,
        supplier_id: values.supplier_id || null,
        vehicle_source_booking: values.vehicle_source_booking || "own",
        status: values.status || "ACTIVE",
        created_by: Number(loggedinuserid) || 1,
        products: products,
      };

      console.log("🔥 FINAL DATA:", data);

      // Call appropriate mutation
      if (mode === "edit") {
        updateBooking.mutate(data);
      } else {
        addBooking.mutate(data);
      }
    } catch (error) {
      console.log("❌ ERROR:", error);
      Toast.fire({
        icon: "error",
        title: "Failed to submit booking",
      });
    }
  };

  const handleBack = () => {
    router.push("/bookings");
    form.reset();
    isInitialized.current = false;
  };

  const isReadOnly = readOnly || mode === "view";

  const companyId =
    mode === "edit"
      ? form.watch("company_id") ?? initialCompanyId
      : form.watch("company_id");

  const customerId =
    mode === "edit"
      ? form.watch("customer_id") ?? initialCustomerId
      : form.watch("customer_id");

  const selectedOrders = form.watch("order_no");

  // Fetch company dropdown
  const { data: companyData, isLoading: companyLoading } = useFetcher(
    "/transaction/booking/company",
    "companyDropdown"
  );

  // Fetch customer dropdown
  const { data: customerData, isLoading: customerLoading } = useFetcher(
    "/transaction/booking/customer",
    "customerDropdown"
  );

  const { data: vehicleData, isLoading: vehicleloading } = useFetcher(
    "/transaction/booking/vehicleno",
    "vehicleDropdown"
  );

  const { data: destinationData, isLoading: destinationloading } = useFetcher(
    "/transaction/booking/destination",
    "destinationDropdown"
  );

  const { data: supplierData, isLoading: supplierloading } = useFetcher(
    "/transaction/booking/supplier",
    "supplierDropdown"
  );

  const { data: productData, isLoading: productdataloading } = useFetcher(
    "/transaction/booking/product",
    "productDropdown"
  );

  const { data: rateTypeData, isLoading: ratetypedataloading } = useFetcher(
    "/transaction/booking/ratetype",
    "ratetypeDropdown"
  );

  const bookingId =
    booking?.booking_id || (param.id ? Number(param.id) : undefined);

  // ✅ ADD THIS - Fetch booking data in EDIT mode
  const { data: bookingData, isLoading: bookingLoading } = useFetcher(
    bookingId && mode === "edit" ? `/transaction/booking/${bookingId}` : "",
    bookingId && mode === "edit" ? `booking-${bookingId}` : "",
    Boolean(bookingId && mode === "edit")
  );

  // Fetch orders when both company and customer are selected
  const enableOrders = Boolean(companyId && customerId);

  const ordersKey = enableOrders
    ? `ordersDropdown-${companyId}-${customerId}`
    : "ordersDropdown-disabled";

  const ordersUrl = enableOrders
    ? `/transaction/booking/orders/${companyId}/${customerId}`
    : "";

  const { data: ordersData, isLoading: ordersLoading } = useFetcher(
    ordersUrl,
    ordersKey,
    enableOrders // controls execution
  );

  console.log(
    "📡 Fetching Orders With:",
    companyId,
    customerId,
    "Enable:",
    enableOrders
  );
  console.log("🔥 Orders API Response:", ordersData);

  // Transform orders data into popup items
  const orderItems = useMemo(() => {
    if (!ordersData?.orders) return [];

    return ordersData.orders.map((o: any) => ({
      id: o.order_id,
      name: o.order_no,
      date: new Date(o.order_date).toLocaleDateString(),

      // ⭐ Use NAMES, not IDs
      from: o.from_destination_name ?? "-",
      to: o.to_destination_name ?? "-",

      raw: o,
    }));
  }, [ordersData]);

  useEffect(() => {
    if (mode !== "add") return;
    if (!selectedOrders || selectedOrders.length === 0) return;

    const firstOrder = selectedOrders[0]?.raw;
    if (!firstOrder) return;

    console.log("📍 Auto-setting destinations from order:", {
      from: firstOrder.from_destination_id,
      to: firstOrder.to_destination_id,
    });

    // ✅ SET DESTINATIONS
    form.setValue(
      "from_destination_id",
      firstOrder.from_destination_id ?? null
    );

    form.setValue("to_destination_id", firstOrder.to_destination_id ?? null);

    // ✅ PRODUCTS (existing logic)
    const allProducts: any[] = [];

    selectedOrders.forEach((o: any) => {
      if (Array.isArray(o.raw?.products)) {
        o.raw.products.forEach((p: any) => {
          allProducts.push({
            booking_product_id: undefined,
            booking_item_no: undefined,
            product_id: p.product_id,
            no_of_packages: p.no_of_packages,
            weight: p.weight,
            rate: p.rate,
            rate_type_id: p.rate_type_id,
            kms: p.kms,
            fright_amount: p.fright_amount,
            remarks: p.remarks ?? "",
            booking_id: undefined,
            order_id: o.raw.order_id,
          });
        });
      }
    });

    if (allProducts.length > 0) {
      replace(allProducts);
    }
  }, [selectedOrders, mode, form, replace]);

  // Reset customer and orders when company changes
  // Reset customer and orders when company changes (ADD mode only)
  useEffect(() => {
    if (mode === "add") {
      form.setValue("customer_id", null);
      form.setValue("order_no", []);
    }
  }, [companyId, form, mode]);

  // Reset orders when customer changes (ADD mode only)
  useEffect(() => {
    if (mode === "add" && form.getValues("order_no")?.length > 0) {
      form.setValue("order_no", []);
    }
  }, [customerId, mode]);

  // Add this useEffect after your existing useEffects

  // ✅ Populate order_no after orders are fetched
  useEffect(() => {
    const sourceData = mode === "edit" ? bookingData?.booking : booking;

    if (
      (mode === "edit" || mode === "view") &&
      sourceData?.order_no &&
      ordersData?.orders
    ) {
      const b = sourceData;
      const currentOrderNo = form.getValues("order_no");

      // Only populate if not already set
      if (!currentOrderNo || currentOrderNo.length === 0) {
        const orderNoArray = b.order_no
          ? b.order_no.split(",").map((orderNo: string) => {
              const trimmedNo = orderNo.trim();
              const matchedOrder = ordersData.orders.find(
                (o: any) => o.order_no === trimmedNo
              );

              if (matchedOrder) {
                return {
                  id: matchedOrder.order_id,
                  name: matchedOrder.order_no,
                  date: new Date(matchedOrder.order_date).toLocaleDateString(),
                  from: matchedOrder.from_destination_name || "-",
                  to: matchedOrder.to_destination_name || "-",
                  raw: matchedOrder,
                };
              }

              return {
                id: 0,
                name: trimmedNo,
                date: "",
                from: "",
                to: "",
                raw: {},
              };
            })
          : [];

        if (orderNoArray.length > 0) {
          form.setValue("order_no", orderNoArray);
          console.log("✅ Populated orders:", orderNoArray);
        }
      }
    }
  }, [mode, bookingData, booking, ordersData, form]);

  // ✅ Initialize form with booking data in EDIT/VIEW mode
  // ✅ Initialize form with booking data in EDIT/VIEW mode
  useEffect(() => {
    if (mode !== "edit" || !bookingData?.booking || isInitialized.current)
      return;

    // ✅ Wait for all dropdown data to load before initializing
    if (
      companyLoading ||
      customerLoading ||
      vehicleloading ||
      destinationloading ||
      productdataloading ||
      ratetypedataloading
    ) {
      return;
    }

    const b = bookingData.booking;

    setInitialCompanyId(b.company_id ?? undefined);
    setInitialCustomerId(b.customer_id ?? undefined);

    form.setValue("company_id", b.company_id ?? undefined);
    form.setValue("customer_id", b.customer_id ?? undefined);

    form.setValue("booking_id", b.booking_id);
    form.setValue("booking_no", b.booking_no ?? "");
    form.setValue(
      "booking_date",
      b.booking_date ? b.booking_date.split("T")[0] : ""
    );

    form.setValue("vehicle_id", b.vehicle_id ?? undefined);
    form.setValue("from_destination_id", b.from_destination_id ?? undefined);
    form.setValue("to_destination_id", b.to_destination_id ?? undefined);
    form.setValue("supplier_id", b.supplier_id ?? undefined);
    form.setValue("vehicle_source_booking", b.vehicle_source_booking ?? "own");
    form.setValue("status", b.status ?? "ACTIVE");

    if (b.products?.length) {
      replace(
        b.products.map((p: any) => ({
          booking_product_id: p.booking_product_id,
          booking_item_no: p.booking_item_no,
          product_id: p.product_id,
          no_of_packages: p.no_of_packages,
          weight: p.weight,
          rate: p.rate,
          rate_type_id: p.rate_type_id,
          kms: p.kms,
          fright_amount: p.fright_amount,
          remarks: p.remarks ?? "",
          booking_id: p.booking_id,
          order_id: p.order_id,
        }))
      );
    }

    isInitialized.current = true;
  }, [
    mode,
    bookingData,
    form,
    replace,
    companyLoading,
    customerLoading,
    vehicleloading,
    destinationloading,
    productdataloading,
    ratetypedataloading,
  ]);

  // ✅ ADD THIS NEW EFFECT after the above
  // Populate order_no after orders are fetched in EDIT mode
  useEffect(() => {
    if (
      mode === "edit" &&
      bookingData?.booking?.order_no &&
      ordersData?.orders
    ) {
      const b = bookingData.booking;
      const currentOrderNo = form.getValues("order_no");

      // Only populate if not already set
      if (!currentOrderNo || currentOrderNo.length === 0) {
        const orderNoArray = b.order_no
          ? b.order_no.split(",").map((orderNo: string) => {
              const trimmedNo = orderNo.trim();
              const matchedOrder = ordersData.orders.find(
                (o: any) => o.order_no === trimmedNo
              );

              if (matchedOrder) {
                return {
                  id: matchedOrder.order_id,
                  name: matchedOrder.order_no,
                  date: new Date(matchedOrder.order_date).toLocaleDateString(),
                  from: matchedOrder.from_destination_name || "-",
                  to: matchedOrder.to_destination_name || "-",
                  raw: matchedOrder,
                };
              }

              return {
                id: 0,
                name: trimmedNo,
                date: "",
                from: "",
                to: "",
                raw: {},
              };
            })
          : [];

        if (orderNoArray.length > 0) {
          form.setValue("order_no", orderNoArray);
          console.log("✅ Populated orders in EDIT mode:", orderNoArray);
        }
      }
    }
  }, [mode, bookingData, ordersData, form]);

  useEffect(() => {
    console.log(form.formState.errors);
  }, [form.formState.errors]);

  useEffect(() => {
    console.log("🔍 Current Form State:", {
      mode,
      company_id: form.getValues("company_id"),
      customer_id: form.getValues("customer_id"),
      vehicle_id: form.getValues("vehicle_id"),
      from_destination_id: form.getValues("from_destination_id"),
      to_destination_id: form.getValues("to_destination_id"),
      initialCompanyId,
      initialCustomerId,
    });
  }, [mode, form, initialCompanyId, initialCustomerId]);

  useEffect(() => {
    if (mode !== "edit" || !booking || !isInitialized.current) return;

    if (companyData?.companies?.length)
      form.setValue("company_id", booking.company_id);

    if (customerData?.customers?.length)
      form.setValue("customer_id", booking.customer_id);

    if (vehicleData?.vehicles?.length)
      form.setValue("vehicle_id", booking.vehicle_id);

    if (destinationData?.destinations?.length) {
      form.setValue("from_destination_id", booking.from_destination_id);
      form.setValue("to_destination_id", booking.to_destination_id);
    }

    if (supplierData?.suppliers?.length && booking.supplier_id) {
      form.setValue("supplier_id", booking.supplier_id);
    }
  }, [
    booking,
    mode,
    companyData,
    customerData,
    vehicleData,
    destinationData,
    supplierData,
    form,
  ]);

  // ✅ Show loading state
  if (mode === "edit" && bookingLoading) {
    return (
      <div className="min-h-screen bg-white dark:bg-gray-950 p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 dark:border-gray-100 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">
            Loading booking data...
          </p>
        </div>
      </div>
    );
  }

  // For VIEW mode, check if booking prop exists
  if (mode === "view" && !booking) {
    return (
      <div className="min-h-screen bg-white dark:bg-gray-950 p-6 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 dark:text-gray-400">
            No booking data available
          </p>
        </div>
      </div>
    );
  }
  return (
    <div
      className="min-h-screen bg-white dark:bg-gray-950 p-6"
      dir={isRTL ? "rtl" : "ltr"}
    >
      <div className="max-w-7xl mx-auto">
        {/* Back Button */}

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit, (errors) => {
              console.log("❌ Form validation errors:", errors);
              Toast.fire({
                icon: "error",
                title: "Please fill all required fields",
              });
            })}
            className="space-y-6"
          >
            {/* FIRST ROW: COMPANY, CUSTOMER, ORDER */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* COMPANY */}
              <FormField
                control={form.control}
                name="company_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Company</FormLabel>
                    <Select
                      onValueChange={(val) => field.onChange(Number(val))}
                      value={field.value ? String(field.value) : ""}
                      disabled={companyLoading}
                    >
                      <FormControl>
                        <SelectTrigger className="h-11">
                          <SelectValue
                            placeholder={
                              companyLoading ? "Loading..." : "Select Company"
                            }
                          />
                        </SelectTrigger>
                      </FormControl>

                      <SelectContent>
                        {companyData?.companies?.length > 0 ? (
                          companyData.companies.map((c: any) => (
                            <SelectItem
                              key={c.company_id}
                              value={String(c.company_id)}
                            >
                              {c.company_name}
                            </SelectItem>
                          ))
                        ) : (
                          <SelectItem value="none" disabled>
                            No companies found
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* CUSTOMER */}
              <FormField
                control={form.control}
                name="customer_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Customer</FormLabel>
                    <Select
                      onValueChange={(val) => field.onChange(Number(val))}
                      value={field.value ? String(field.value) : ""}
                      disabled={!companyId || customerLoading}
                    >
                      <FormControl>
                        <SelectTrigger className="h-11">
                          <SelectValue
                            placeholder={
                              !companyId
                                ? "Select company first"
                                : customerLoading
                                ? "Loading..."
                                : "Select Customer"
                            }
                          />
                        </SelectTrigger>
                      </FormControl>

                      <SelectContent>
                        {customerData?.customers?.length > 0 ? (
                          customerData.customers.map((cu: any) => (
                            <SelectItem
                              key={cu.customer_id}
                              value={String(cu.customer_id)}
                            >
                              {cu.customer_name}
                            </SelectItem>
                          ))
                        ) : (
                          <SelectItem value="none" disabled>
                            No customers found
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* ORDER SELECT POPUP */}
              <FormField
                control={form.control}
                name="order_no"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Order</FormLabel>
                    <FormControl>
                      <input
                        type="text"
                        readOnly
                        onClick={() => {
                          if (companyId && customerId) {
                            setOpenOrderPopup(true);
                          }
                        }}
                        value={
                          Array.isArray(field.value)
                            ? field.value.map((o: any) => o.name).join(", ")
                            : ""
                        }
                        placeholder={
                          !companyId || !customerId
                            ? "Select company & customer first"
                            : ordersLoading
                            ? "Loading orders..."
                            : orderItems.length === 0
                            ? "No orders found"
                            : "Click to select orders"
                        }
                        disabled={!companyId || !customerId}
                        className={cn(
                          "h-11 w-full border px-3 rounded",
                          companyId && customerId && !ordersLoading
                            ? "cursor-pointer"
                            : "cursor-not-allowed bg-gray-100"
                        )}
                      />
                    </FormControl>

                    <MultiSelectPopup
                      open={openOrderPopup}
                      onClose={setOpenOrderPopup}
                      items={orderItems}
                      field={field}
                    />
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Rest of form... */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="booking_no"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Booking No</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        placeholder="Enter Booking No."
                        className="h-11"
                      />
                    </FormControl>
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="booking_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Booking Date</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} className="w-36 h-11" />
                    </FormControl>
                  </FormItem>
                )}
              />

              {/* VEHICLE SOURCE */}
              <FormField
                control={form.control}
                name="vehicle_source_booking"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Vehicle Source</FormLabel>
                    <div className="flex gap-6">
                      <label className="flex items-center gap-2">
                        <input
                          type="radio"
                          value="own"
                          checked={field.value === "own"}
                          onChange={() => field.onChange("own")}
                        />
                        Own Vehicle
                      </label>

                      <label className="flex items-center gap-2">
                        <input
                          type="radio"
                          value="hire"
                          checked={field.value === "hire"}
                          onChange={() => field.onChange("hire")}
                        />
                        Hire Vehicle
                      </label>
                    </div>
                  </FormItem>
                )}
              />

              {/* SUPPLIER — visible only if hire */}
              {form.watch("vehicle_source_booking") === "hire" && (
                <FormField
                  control={form.control}
                  name="supplier_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Supplier</FormLabel>

                      <Select
                        onValueChange={(v) => field.onChange(Number(v))}
                        value={field.value ? String(field.value) : ""}
                        disabled={supplierloading}
                      >
                        <FormControl>
                          <SelectTrigger className="h-11">
                            <SelectValue
                              placeholder={
                                supplierloading
                                  ? "Loading suppliers..."
                                  : "Select Supplier"
                              }
                            />
                          </SelectTrigger>
                        </FormControl>

                        <SelectContent>
                          {supplierData?.suppliers?.length > 0 ? (
                            supplierData.suppliers.map((s: any) => (
                              <SelectItem
                                key={s.supplier_id}
                                value={String(s.supplier_id)}
                              >
                                {s.supplier_name}
                              </SelectItem>
                            ))
                          ) : (
                            <SelectItem value="none" disabled>
                              No suppliers found
                            </SelectItem>
                          )}
                        </SelectContent>
                      </Select>

                      <FormMessage /> 
                    </FormItem>
                  )}
                />
              )}
            </div>

            {/* Destinations */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="vehicle_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Vehicle Number</FormLabel>

                    <Select
                      onValueChange={(val) => field.onChange(Number(val))}
                      value={field.value ? String(field.value) : ""}
                      disabled={vehicleloading}
                    >
                      <FormControl>
                        <SelectTrigger className=" h-11">
                          <SelectValue
                            placeholder={
                              vehicleloading
                                ? "Loading vehicles..."
                                : "Select Vehicle Number"
                            }
                          />
                        </SelectTrigger>
                      </FormControl>

                      <SelectContent>
                        {vehicleData?.vehicles?.length > 0 ? (
                          vehicleData.vehicles.map((v: any) => (
                            <SelectItem
                              key={v.vehicle_id}
                              value={String(v.vehicle_id)}
                            >
                              {v.vehicle_no}
                            </SelectItem>
                          ))
                        ) : (
                          <SelectItem value="none" disabled>
                            No vehicles found
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />

              {/* FROM DESTINATION */}
              <FormField
                control={form.control}
                name="from_destination_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Destination From</FormLabel>
                    <Select
                      onValueChange={(val) => field.onChange(Number(val))}
                      value={field.value ? String(field.value) : ""}
                      disabled={!companyId || destinationloading}
                    >
                      <FormControl>
                        <SelectTrigger className="h-11">
                          <SelectValue
                            placeholder={
                              !companyId
                                ? "Select company first"
                                : destinationloading
                                ? "Loading..."
                                : "Select Destination"
                            }
                          />
                        </SelectTrigger>
                      </FormControl>

                      <SelectContent>
                        {destinationData?.destinations?.length > 0 ? (
                          destinationData.destinations.map((des: any) => (
                            <SelectItem
                              key={des.destination_id}
                              value={String(des.destination_id)}
                            >
                              {des.destination}
                            </SelectItem>
                          ))
                        ) : (
                          <SelectItem value="none" disabled>
                            No destination found
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />

              {/* TO DESTINATION */}
              <FormField
                control={form.control}
                name="to_destination_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Destination To</FormLabel>
                    <Select
                      onValueChange={(val) => field.onChange(Number(val))}
                      value={field.value ? String(field.value) : ""}
                      disabled={!companyId || destinationloading}
                    >
                      <FormControl>
                        <SelectTrigger className="h-11">
                          <SelectValue
                            placeholder={
                              !companyId
                                ? "Select company first"
                                : destinationloading
                                ? "Loading..."
                                : "Select Destination"
                            }
                          />
                        </SelectTrigger>
                      </FormControl>

                      <SelectContent>
                        {destinationData?.destinations?.length > 0 ? (
                          destinationData.destinations.map((des: any) => (
                            <SelectItem
                              key={des.destination_id}
                              value={String(des.destination_id)}
                            >
                              {des.destination}
                            </SelectItem>
                          ))
                        ) : (
                          <SelectItem value="none" disabled>
                            No destination found
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                  </FormItem>
                )}
              />
            </div>

            {/* Product Table */}
            <div className="space-y-4">
              <div className="pt-4">
                <h2 className="text-base font-normal text-gray-900 dark:text-gray-100">
                  Product / Package Detail
                </h2>
              </div>

              {/* Table Header */}
              <div className="grid grid-cols-10 bg-gray-200 text-xs font-semibold">
                <div className="p-2 border">Product Name</div>
                <div className="p-2 border">Packages</div>
                <div className="p-2 border">Weight</div>
                <div className="p-2 border">Rate Type</div>
                <div className="p-2 border">Rate</div>
                <div className="p-2 border">KMs</div>
                <div className="p-2 border">Freight</div>
                <div className="p-2 border">Remarks</div>
                <div className="p-2 border text-center">+</div>
                <div className="p-2 border text-center">×</div>
              </div>

              {/* Table Rows */}
              {fields.map((row, index) => (
                <div key={row.id} className="grid grid-cols-10 text-sm">
                  {/* Hidden field for booking_product_id */}
                  <input
                    type="hidden"
                    {...register(`products.${index}.booking_product_id`)}
                  />
                  <input
                    type="hidden"
                    {...register(`products.${index}.order_id`)}
                  />

                  {/* PRODUCT NAME */}
                  {/* PRODUCT */}
                  {/* PRODUCT */}
                  <div className="p-2 border">
                    <FormField
                      control={form.control}
                      name={`products.${index}.product_id`}
                      render={({ field }) => (
                        <FormItem>
                          <Select
                            value={
                              field.value !== undefined && field.value !== null
                                ? String(field.value)
                                : ""
                            }
                            onValueChange={(val) => field.onChange(Number(val))}
                            disabled={isReadOnly || productdataloading}
                          >
                            <FormControl>
                              <SelectTrigger className="h-9 text-xs">
                                <SelectValue
                                  placeholder={
                                    productdataloading
                                      ? "Loading..."
                                      : "Select Product"
                                  }
                                />
                              </SelectTrigger>
                            </FormControl>

                            <SelectContent>
                              {productData?.product?.length > 0 ? (
                                productData.product.map((p: any) => (
                                  <SelectItem
                                    key={p.product_id}
                                    value={String(p.product_id)}
                                  >
                                    {p.product_name}
                                  </SelectItem>
                                ))
                              ) : (
                                <SelectItem value="none" disabled>
                                  {productdataloading
                                    ? "Loading..."
                                    : "No products found"}
                                </SelectItem>
                              )}
                            </SelectContent>
                          </Select>
                        </FormItem>
                      )}
                    />
                  </div>

                  {/* PACKAGES */}
                  <div className="p-2 border">
                    <input
                      type="number"
                      {...register(`products.${index}.no_of_packages`, {
                        valueAsNumber: true,
                      })}
                      className="w-full h-9 text-xs border rounded px-2"
                      disabled={isReadOnly}
                      placeholder="0"
                    />
                  </div>

                  {/* WEIGHT */}
                  <div className="p-2 border">
                    <input
                      type="number"
                      step="0.01"
                      {...register(`products.${index}.weight`, {
                        valueAsNumber: true,
                      })}
                      className="w-full h-9 text-xs border rounded px-2"
                      disabled={isReadOnly}
                      placeholder="0.00"
                    />
                  </div>

                  {/* RATE TYPE */}
                  {/* RATE TYPE */}
                  <div className="p-2 border">
                    <FormField
                      control={form.control}
                      name={`products.${index}.rate_type_id`}
                      render={({ field }) => (
                        <FormItem>
                          <Select
                            value={
                              field.value !== undefined && field.value !== null
                                ? String(field.value)
                                : ""
                            }
                            onValueChange={(val) => field.onChange(Number(val))}
                            disabled={isReadOnly || ratetypedataloading}
                          >
                            <FormControl>
                              <SelectTrigger className="h-9 text-xs">
                                <SelectValue
                                  placeholder={
                                    ratetypedataloading
                                      ? "Loading..."
                                      : "Select Rate Type"
                                  }
                                />
                              </SelectTrigger>
                            </FormControl>

                            <SelectContent>
                              {rateTypeData?.rate_type?.length > 0 ? (
                                rateTypeData.rate_type.map((rt: any) => (
                                  <SelectItem
                                    key={rt.rate_type_id}
                                    value={String(rt.rate_type_id)}
                                  >
                                    {rt.rate_type}
                                  </SelectItem>
                                ))
                              ) : (
                                <SelectItem value="none" disabled>
                                  {ratetypedataloading
                                    ? "Loading..."
                                    : "No rate types found"}
                                </SelectItem>
                              )}
                            </SelectContent>
                          </Select>
                        </FormItem>
                      )}
                    />
                  </div>

                  {/* RATE */}
                  <div className="p-2 border">
                    <input
                      type="number"
                      step="0.01"
                      {...register(`products.${index}.rate`, {
                        valueAsNumber: true,
                      })}
                      className="w-full h-9 text-xs border rounded px-2"
                      disabled={isReadOnly}
                      placeholder="0.00"
                    />
                  </div>

                  {/* KMS */}
                  <div className="p-2 border">
                    <input
                      type="number"
                      step="0.01"
                      {...register(`products.${index}.kms`, {
                        valueAsNumber: true,
                      })}
                      className="w-full h-9 text-xs border rounded px-2"
                      disabled={isReadOnly}
                      placeholder="0.00"
                    />
                  </div>

                  {/* FREIGHT */}
                  <div className="p-2 border">
                    <input
                      type="number"
                      step="0.01"
                      {...register(`products.${index}.fright_amount`, {
                        valueAsNumber: true,
                      })}
                      className="w-full h-9 text-xs border rounded px-2"
                      disabled={isReadOnly}
                      placeholder="0.00"
                    />
                  </div>

                  {/* REMARKS */}
                  <div className="p-2 border">
                    <input
                      {...register(`products.${index}.remarks`)}
                      className="w-full h-9 text-xs border rounded px-2"
                      disabled={isReadOnly}
                      placeholder="Remarks"
                    />
                  </div>

                  {/* ADD ROW - Show only on last row */}
                  <div className="p-2 border flex justify-center items-center">
                    {/* {index === fields.length - 1 && !isReadOnly && (
                      <button
                        type="button"
                        onClick={() =>
                          append({
                            booking_product_id: undefined,
                            booking_item_no: undefined,
                            product_id: null,
                            no_of_packages: undefined,
                            weight: undefined,
                            rate: undefined,
                            rate_type_id: undefined,
                            kms: undefined,
                            fright_amount: undefined,
                            remarks: "",
                            booking_id: undefined,
                            order_id: undefined,
                          })
                        }
                        className="w-7 h-7 flex items-center justify-center bg-green-500 hover:bg-green-600 text-white rounded transition-colors"
                        title="Add new product row"
                      >
                        +
                      </button>
                    )} */}
                  </div>

                  {/* DELETE ROW */}
                  {/* DELETE ROW */}
                  <div className="p-2 border flex justify-center items-center">
                    {!isReadOnly && (
                      <button
                        type="button"
                        disabled={Boolean(
                          form.getValues(`products.${index}.order_id`)
                        )}
                        onClick={() => remove(index)}
                        className="w-7 h-7 bg-red-500 disabled:opacity-50"
                        title="Order products cannot be deleted"
                      >
                        ×
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex gap-3 pt-6">
              <Button
                type="submit"
                className="h-10 px-6 bg-gray-900 text-white"
              >
                Save
              </Button>
              <Button type="button" variant="outline" onClick={handleBack}>
                Close
              </Button>
            </div>
          </form>
        </Form>
      </div>
    </div>
  );
};

export default BookingForm;
