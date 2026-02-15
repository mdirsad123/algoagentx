"use client";

import React, { useEffect, useState, useMemo } from "react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";
import Cookies from "js-cookie";
import moment from "moment";

import { DataTable } from "@/components/shared/data-table";
import { Input } from "@/components/ui/input";
import DatePicker from "@/components/ui/date-picker";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

import { useFetcher, usePoster } from "@/hooks/use-query";
import { Order } from "@/types/order-type";
import { orderColumns } from "../columns";
import { OrderSchema } from "@/schemas/order-schema";

type FormInputs = z.infer<typeof OrderSchema>;

export const OrderTable = () => {
  const router = useRouter();

  const [showFilter, setShowFilter] = useState(true);
  const [filteredList, setFilteredList] = useState<Order[]>([]);
  const [masterList, setMasterList] = useState<Order[]>([]);

  const form = useForm<FormInputs>({
    defaultValues: {},
  });

  /** Fetch dropdowns */
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

  
  /** Fetch main order list */
  const {
    data: orderListData,
    isLoading,
    refetch,
  } = useFetcher(`/order/orderlist`, "orderList");

  useEffect(() => {
    if (orderListData) {
      setMasterList(orderListData);
    }
  }, [orderListData]);

  const handleRowEdit = (row: Order | any) => {
    router.push(`/transactions/orders/edit/${row.order_id}`);
  };

  const handleRowView = (row: Order | any) => {
    router.push(`/transactions/orders/${row.order_id}`);
  };
  /** Filter API */
  const onSuccess = (response: Order[]) => {
    setFilteredList(response ?? []);
  };

  const onError = () => {
    setFilteredList([]);
  };

  const searchOrder = usePoster(
    "/order/list",
    "orderfilter",
    onSuccess,
    onError
  );

  /** Apply filters */
  const onSubmit = (values: FormInputs) => {
    const data = {
      ...values,
      dispatch_from: values.dispatch_from
        ? moment(values.dispatch_from).format("YYYY-MM-DD")
        : null,
      dispatch_to: values.dispatch_to
        ? moment(values.dispatch_to).format("YYYY-MM-DD")
        : null,
    };

    searchOrder.mutate(data);
  };

  /** Final table data (main requirement) */
  const tableData =
    filteredList && filteredList.length > 0 ? filteredList : masterList;

  return (
    <section className="bg-white max-w-full dark:bg-gray-800 rounded-lg shadow-sm">
      {/* FILTER HEADER */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50 rounded-t-lg">
        <h2 className="text-lg font-semibold text-gray-700">Filter</h2>

        <button
          type="button"
          onClick={() => setShowFilter((prev) => !prev)}
          className="px-4 py-2 text-sm rounded-md bg-primary text-white hover:bg-primary/90"
        >
          {showFilter ? "Hide Filter" : "Show Filter"}
        </button>
      </div>

      {/* FILTER CONTAINER */}
      {showFilter && (
        <div className="px-4 pt-4 pb-2 border-b bg-white transition-all duration-200">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              {/* ROW 1 */}
              <div className="grid grid-cols-4 gap-4">
                {/* Order No */}
                <FormField
                  control={form.control}
                  name="order_no"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="Order No."
                          className="h-11 rounded-lg"
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* Company */}
                <FormField
                  control={form.control}
                  name="company_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Select
                          onValueChange={(val) =>
                            field.onChange(val === "all" ? "" : val)
                          }
                          value={field.value ? String(field.value) : ""}
                        >
                          <SelectTrigger className="h-11 rounded-lg">
                            <SelectValue placeholder="Select Company" />
                          </SelectTrigger>

                          <SelectContent>
                            {/* ---- SELECT ALL OPTION ---- */}
                            <SelectItem value="all">All Companies</SelectItem>

                            {/* ---- NORMAL COMPANY OPTIONS ---- */}
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
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* Customer */}
                <FormField
                  control={form.control}
                  name="customer_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Select
                          onValueChange={(val) =>
                            field.onChange(val === "all" ? "" : val)
                          }
                          value={field.value ? String(field.value) : ""}
                        >
                          <SelectTrigger className="h-11 rounded-lg">
                            <SelectValue placeholder="Select Customer" />
                          </SelectTrigger>

                          <SelectContent>
                            {/* SELECT ALL OPTION */}
                            <SelectItem value="all">All Customers</SelectItem>

                            {/* CUSTOMER LIST */}
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
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* Dispatch From */}
                <FormField
                  control={form.control}
                  name="dispatch_from"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <DatePicker
                          className="h-11 w-full rounded-lg"
                          placeholder="Dispatch From"
                          selected={field.value}
                          onSelect={field.onChange}
                          mode="single"
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />
              </div>

              {/* ROW 2 */}
              <div className="grid grid-cols-4 gap-4">
                {/* Dispatch To */}
                <FormField
                  control={form.control}
                  name="dispatch_to"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <DatePicker
                          className="h-11 w-full rounded-lg"
                          placeholder="Dispatch To"
                          selected={field.value}
                          onSelect={field.onChange}
                          mode="single"
                        />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* Destination From */}
              <FormField
  control={form.control}
  name="from_destination_id"
  render={({ field }) => (
    <FormItem>
      <FormControl>
        <Select
          value={field.value ? String(field.value) : ""}
          onValueChange={(val) => field.onChange(Number(val))}
        >
          <SelectTrigger className="h-11 rounded-lg">
            <SelectValue placeholder="From Location" />
          </SelectTrigger>

          <SelectContent>
            {destinationList?.map((item: any) => (
              <SelectItem
                key={item.id}
                value={String(item.id)} // must be string
              >
                {item.destination}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FormControl>
    </FormItem>
  )}
/>


                {/* Destination To */}
                <FormField
                  control={form.control}
                  name="to_destination_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                       <Select
          value={field.value ? String(field.value) : ""}
          onValueChange={(val) => field.onChange(Number(val))}
        >
                          <SelectTrigger className="h-11 rounded-lg">
                            <SelectValue placeholder="To Location" />
                          </SelectTrigger>
                          <SelectContent>
                            {destinationList?.map((item: any) => (
                              <SelectItem
                                key={item.id}
                                value={item.destination}
                              >
                                {item.destination}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormControl>
                    </FormItem>
                  )}
                />

                <div className="flex justify-end">
                  <button
                    type="submit"
                    className="h-11 w-full bg-primary text-white rounded-lg"
                  >
                    Search
                  </button>
                </div>
              </div>
            </form>
          </Form>
        </div>
      )}

      {/* DATA TABLE */}
      <DataTable
         columns={orderColumns({
          onView: handleRowView,
          onEdit: handleRowEdit,
        })}
        data={tableData}
        showSearch={false}
        showPagination={true}
        paginationOptions={{ showRowCount: true, showPageSize: true }}
        exportOptions={{
          csv: true,
          pdf: true,
          filename: "orders",
          title: "Order List",
        }}
      />
    </section>
  );
};
