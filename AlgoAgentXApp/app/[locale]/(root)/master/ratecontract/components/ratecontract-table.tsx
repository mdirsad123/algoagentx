"use client";
import { DataTable } from "@/components/shared/data-table";

import React, { useEffect, useMemo, useState } from "react";

import { useRouter } from "next/navigation";
import {RotateCcw } from "lucide-react";
import {useFetcher, usePoster } from "@/hooks/use-query";
import { useForm } from "react-hook-form";
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
import { RateContractType } from "@/types/ratecontract-type";
import { RateContractColumns } from "../columns";
import { z } from "zod";
import {
  RateContractSchema,
  RateContractSerchSchema,
} from "@/schemas/ratecontract-schema";

type Props = { ratecontractlist: any };
const RateContractTable = ({ ratecontractlist }: Props) => {
  const router = useRouter();
  type FormInputs = z.infer<typeof RateContractSerchSchema>;
  const form = useForm<FormInputs>();
  const [spinning, setSpinning] = useState(false);

  const [dataList, setDataList] = useState([] as RateContractType[]);

  const onSuccess = (response: RateContractType[]) => {
    setDataList(response);
    console.log("response", response);
  };

  const onError = () => {};

  const searchRateContract = usePoster(
    "/ratecontract/ratecontract-list",
    "RateContractList",
    onSuccess,
    onError
  );

  const onSubmit = (values: FormInputs) => {
    try {
      searchRateContract.mutate(values);
    } catch (error) {
      console.log(error);
    }
  };

  

  const handleRowEdit = (row: RateContractType) => {
    router.push(`/master/ratecontract/edit/${row.ratecontract_id}`); // Add ?from=company
  };

    const handleOnView = (row: RateContractType) => {
    router.push(`/master/ratecontract/${row.ratecontract_id}`); // Add ?from=company
  }

  const { data: customerdropdown } = useFetcher(
    `/customer/get-customer-dropdown`,
    "customer/dropdown"
  );

  const { data: productdropdown } = useFetcher(
    `/ratecontract/get-product-dropdown`,
    "ratecontractdropdown"
  );

  const { data: fromtodestinationdropdown } = useFetcher(
    `/ratecontract/get-fromtodestination-dropdown`,
    "fromtodestinationdropdown"
  );

  useEffect(() => {
    searchRateContract.mutate({}); // ✅ empty body = fetch all data
  }, []);

  const handleResetFilter = () => {
    setSpinning(true);
    form.reset({
      customer_id: "",
      product_id: "",
      from_destination_id: "",
      to_destination_id: "",
    });

    // fetch all data again
    searchRateContract.mutate({});
    setTimeout(() => setSpinning(false), 600);
  };

  return (
    <div className="flex flex-col">
      <section>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="max-w-full">
            <div className="w-full px-4 py-3">
              {/* FILTER ROW */}
              <div className="grid grid-cols-5 gap-4 items-end">
                {/* CUSTOMER */}
                <FormField
                  control={form.control}
                  name="customer_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Select
                          value={field.value}
                          onValueChange={field.onChange}
                        >
                          <SelectTrigger className="h-9">
                            <SelectValue placeholder="Select Customer" />
                          </SelectTrigger>
                          <SelectContent>
                            {customerdropdown?.map((item: any) => (
                              <SelectItem
                                key={item.customer_id}
                                value={item.customer_id.toString()}
                              >
                                {item.customer_name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* PRODUCT */}
                <FormField
                  control={form.control}
                  name="product_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Select
                          value={field.value}
                          onValueChange={field.onChange}
                        >
                          <SelectTrigger className="h-9">
                            <SelectValue placeholder="Select Product" />
                          </SelectTrigger>
                          <SelectContent>
                            {productdropdown?.map((item: any) => (
                              <SelectItem
                                key={item.product_id}
                                value={item.product_id.toString()}
                              >
                                {item.product_name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* FROM DESTINATION */}
                <FormField
                  control={form.control}
                  name="from_destination_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Select
                          value={field.value}
                          onValueChange={field.onChange}
                        >
                          <SelectTrigger className="h-9">
                            <SelectValue placeholder="From Destination" />
                          </SelectTrigger>
                          <SelectContent>
                            {fromtodestinationdropdown?.map((p: any) => (
                              <SelectItem
                                key={p.destination_id}
                                value={p.destination_id.toString()}
                              >
                                {p.destination}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* TO DESTINATION */}
                <FormField
                  control={form.control}
                  name="to_destination_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <Select
                          value={field.value}
                          onValueChange={field.onChange}
                        >
                          <SelectTrigger className="h-9">
                            <SelectValue placeholder="To Destination" />
                          </SelectTrigger>
                          <SelectContent>
                            {fromtodestinationdropdown?.map((p: any) => (
                              <SelectItem
                                key={p.destination_id}
                                value={p.destination_id.toString()}
                              >
                                {p.destination}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* SEARCH BUTTON */}
                {/* SEARCH & RESET BUTTONS */}
                <div className="flex gap-2">
                  <button
                    type="submit"
                    className="h-9 w-full bg-orange-600 text-white rounded-md shadow hover:bg-orange-700 transition"
                  >
                    Search
                  </button>

                  <button
                    type="button"
                    onClick={handleResetFilter}
                    title="Reset filters"
                    className="h-9 w-9 flex items-center justify-center bg-gray-200 text-orange-600 rounded-md shadow hover:bg-gray-300 transition"
                  >
                    <RotateCcw
                      size={16}
                      className={
                        spinning
                          ? "animate-spin [animation-direction:reverse]"
                          : ""
                      }
                    />
                  </button>
                </div>
              </div>
            </div>
          </form>
        </Form>

        {/* Data Table */}

        <DataTable
          columns={RateContractColumns({onEdit: handleRowEdit })}
          data={dataList}
          showSearch={false}
          showPagination={true}
          paginationOptions={{ showRowCount: true, showPageSize: true }}
          exportOptions={{
            csv: true,
            pdf: true,
            filename: "ratecontract",
            title: "Rate Contract List",
          }}
        />
      </section>
    </div>
  );
};

export default RateContractTable;
