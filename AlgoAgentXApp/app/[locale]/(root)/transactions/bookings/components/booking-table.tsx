"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { DataTable } from "@/components/shared/data-table";
import {
  Form,
  FormField,
  FormItem,
  FormControl,
  FormLabel,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { useFetcher, usePoster } from "@/hooks/use-query";
import Toast from "@/components/shared/toast";
import { Booking } from "@/types/booking.type";
import { BookingColumn } from "../columns";
import { RotateCcw } from "lucide-react";

type Props = {
  bookinglist: Booking[];
};

const BookingTable = ({ bookinglist }: Props) => {
  const router = useRouter();

  /* ---------------- FORM ---------------- */
  const form = useForm<Partial<Booking>>({});

  /* ---------------- STATE ---------------- */
  const [bookingData, setBookingData] = useState<Booking[]>(bookinglist);

  /* ---------------- DROPDOWNS ---------------- */
  const { data: customerData } = useFetcher(
    "/transaction/booking/customer",
    "customerDropdown"
  );

  const { data: destinationData } = useFetcher(
    "/transaction/booking/destination",
    "destinationDropdown"
  );

  const { data: supplierData } = useFetcher(
    "/transaction/booking/supplier",
    "supplierDropdown"
  );

  const { data: bookingnoData } = useFetcher(
    "/transaction/booking/bookingno",
    "bookingnoDropdown"
  );

  // Debug logs
  useEffect(() => {
    console.log("destinationData:", destinationData);
    console.log("bookingnoData:", bookingnoData);
  }, [destinationData, bookingnoData]);

  /* ---------------- SEARCH API ---------------- */
  const searchBookings = usePoster(
    "/transaction/booking/booking-list",
    "bookingList",
    (data: Booking[]) => {
      setBookingData(data);
    },
    () => {
      Toast.fire({
        icon: "error",
        title: "Failed to fetch bookings",
      });
    }
  );

  /* ---------------- SUBMIT ---------------- */
  const onSearch = (values: Partial<Booking>) => {
    searchBookings.mutate({
      booking_no: values.booking_no,
      customer_id: values.customer_id,
      from_destination_id: values.from_destination_id,
      to_destination_id: values.to_destination_id,
      supplier_id: values.supplier_id,
      status: values.status,
    });
  };

  /* ---------------- RESET ---------------- */
  const handleReset = () => {
    form.reset({
      booking_id: undefined,
      customer_id: undefined,
      from_destination_id: undefined,
      to_destination_id: undefined,
      supplier_id: undefined,
      status: undefined,
    });
    setBookingData(bookinglist);
  };

  /* ---------------- ROW ACTIONS ---------------- */
  const handleRowView = (row: Booking) => {
    router.push(`/transactions/bookings/${row.booking_id}`);
  };

  const handleRowEdit = (row: Booking) => {
    router.push(`/transactions/bookings/edit/${row.booking_id}`);
  };

  return (
    <div className="p-5 space-y-4">
      {/* 🔍 FILTER FORM */}
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSearch)}
          className="grid grid-cols-1 md:grid-cols-6 gap-3"
        >
          {/* BOOKING NO */}
          <FormField
            control={form.control}
            name="booking_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Booking No</FormLabel>
                <Select
                  value={field.value ? String(field.value) : "__select__"}
                  onValueChange={(v) => field.onChange(v === "__select__" ? undefined : Number(v))}
                >
                  <FormControl>
                    <SelectTrigger className="h-11">
                      <SelectValue placeholder="--Select--" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="__select__">--Select--</SelectItem>
                    {bookingnoData?.booking?.length ? (
                      bookingnoData.booking.map((b: any) => (
                        <SelectItem
                          key={b.booking_id}
                          value={String(b.booking_id)}
                        >
                          {b.booking_no}
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="__none__" disabled>
                        No bookings found
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
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
                  value={field.value ? String(field.value) : "__select__"}
                  onValueChange={(v) => field.onChange(v === "__select__" ? undefined : Number(v))}
                >
                  <FormControl>
                    <SelectTrigger className="h-11">
                      <SelectValue placeholder="--Select--" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="__select__">--Select--</SelectItem>
                    {customerData?.customers?.length ? (
                      customerData.customers.map((c: any) => (
                        <SelectItem
                          key={c.customer_id}
                          value={String(c.customer_id)}
                        >
                          {c.customer_name}
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="__none__" disabled>
                        No customers found
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </FormItem>
            )}
          />

          {/* FROM */}
          <FormField
            control={form.control}
            name="from_destination_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>From</FormLabel>
                <Select
                  value={field.value ? String(field.value) : "__select__"}
                  onValueChange={(v) => field.onChange(v === "__select__" ? undefined : Number(v))}
                >
                  <FormControl>
                    <SelectTrigger className="h-11">
                      <SelectValue placeholder="--Select--" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent className="max-h-[200px]">
                    <SelectItem value="__select__">--Select--</SelectItem>
                    {destinationData?.destinations?.length > 0 ? (
                      destinationData.destinations.map((d: any) => (
                        <SelectItem
                          key={d.destination_id}
                          value={String(d.destination_id)}
                        >
                          {d.destination}
                        </SelectItem>
                      ))
                    ) : Array.isArray(destinationData) && destinationData.length > 0 ? (
                      destinationData.map((d: any) => (
                        <SelectItem
                          key={d.destination_id}
                          value={String(d.destination_id)}
                        >
                          {d.destination}
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="__none__" disabled>
                        No destinations found
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </FormItem>
            )}
          />

          {/* TO */}
          <FormField
            control={form.control}
            name="to_destination_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>To</FormLabel>
                <Select
                  value={field.value ? String(field.value) : "__select__"}
                  onValueChange={(v) => field.onChange(v === "__select__" ? undefined : Number(v))}
                >
                  <FormControl>
                    <SelectTrigger className="h-11">
                      <SelectValue placeholder="--Select--" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent className="max-h-[200px]">
                    <SelectItem value="__select__">--Select--</SelectItem>
                    {destinationData?.destinations?.length > 0 ? (
                      destinationData.destinations.map((d: any) => (
                        <SelectItem
                          key={d.destination_id}
                          value={String(d.destination_id)}
                        >
                          {d.destination}
                        </SelectItem>
                      ))
                    ) : Array.isArray(destinationData) && destinationData.length > 0 ? (
                      destinationData.map((d: any) => (
                        <SelectItem
                          key={d.destination_id}
                          value={String(d.destination_id)}
                        >
                          {d.destination}
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="__none__" disabled>
                        No destinations found
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </FormItem>
            )}
          />

          {/* SUPPLIER */}
          <FormField
            control={form.control}
            name="supplier_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Supplier</FormLabel>
                <Select
                  value={field.value ? String(field.value) : "__select__"}
                  onValueChange={(v) => field.onChange(v === "__select__" ? undefined : Number(v))}
                >
                  <FormControl>
                    <SelectTrigger className="h-11">
                      <SelectValue placeholder="--Select--" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="__select__">--Select--</SelectItem>
                    {supplierData?.suppliers?.length ? (
                      supplierData.suppliers.map((s: any) => (
                        <SelectItem
                          key={s.supplier_id}
                          value={String(s.supplier_id)}
                        >
                          {s.supplier_name}
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="__none__" disabled>
                        No suppliers found
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </FormItem>
            )}
          />

          {/* STATUS */}
          <FormField
            control={form.control}
            name="status"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Status</FormLabel>
                <Select
                  value={field.value ?? "__select__"}
                  onValueChange={(v) => field.onChange(v === "__select__" ? undefined : v)}
                >
                  <FormControl>
                    <SelectTrigger className="h-11">
                      <SelectValue placeholder="--Select--" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="__select__">--Select--</SelectItem>
                    <SelectItem value="BOOKED">Booked</SelectItem>
                    <SelectItem value="CANCELLED">Cancelled</SelectItem>
                  </SelectContent>
                </Select>
              </FormItem>
            )}
          />

          {/* BUTTONS */}
          <div className="flex items-end gap-2">
            <button
              type="submit"
              className="h-11 flex-1 rounded-md bg-primary text-white font-medium hover:bg-primary/90 transition-colors"
              disabled={searchBookings.isLoading}
            >
              {searchBookings.isLoading ? "Searching..." : "Search"}
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="h-11 w-11 rounded-md bg-gray-200 hover:bg-gray-300 transition-colors flex items-center justify-center"
              title="Reset filters"
            >
              <RotateCcw className="h-4 w-4 text-gray-700" />
            </button>
          </div>
        </form>
      </Form>

      {/* 📋 TABLE */}
      <DataTable
        columns={BookingColumn({
          onView: handleRowView,
          onEdit: handleRowEdit,
        })}
        data={bookingData}
        showPagination
        paginationOptions={{ showRowCount: true, showPageSize: true }}
        exportOptions={{
          pdf: true,
          csv: true,
          filename: "Booking List",
          title: "Booking List",
        }}
      />
    </div>
  );
};

export default BookingTable;