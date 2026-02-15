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

import React, { useEffect, useState } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { useFetcher, usePoster } from "@/hooks/use-query";
import { z } from "zod";
import { RateContractSchema } from "@/schemas/ratecontract-schema";
import Toast from "@/components/shared/toast";
import { RateContractType } from "@/types/ratecontract-type";
import { zodResolver } from "@hookform/resolvers/zod";
import Cookies from "js-cookie";
import { useUpdater } from "@/hooks/use-query";
import { useRouter } from "next/navigation";
import { useParams, useSearchParams } from "next/navigation";

type RateContractFormProps = {
  RateContactEdit?: RateContractType;
};

export default function RateContract({
  RateContactEdit,
}: RateContractFormProps) {
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));
  const param = useParams();
  const router = useRouter();

  type RateDetailInput = {
    from_destination_id: string | number;
    to_destination_id: string | number;
    actual_kms: string | number;
    billing_kms: string | number;
    rate_type_id: string | number;
    rate_amt: string | number;
    toll_tax?: string | number;
  };

  type FormInputs = {
    customer_id: number | "";
    product_id: number | "";
    effective_date: Date | undefined;
    rate_details: RateDetailInput[];
  };

  const form = useForm<FormInputs>({
    resolver: zodResolver(RateContractSchema),

    defaultValues: RateContactEdit
      ? {
          customer_id: RateContactEdit.customer_id,
          product_id: RateContactEdit.product_id,
          effective_date: RateContactEdit.effective_date,

          rate_details: RateContactEdit.rate_details?.length
            ? RateContactEdit.rate_details.map((item: any) => ({
                from_destination_id: item.from_destination_id,
                to_destination_id: item.to_destination_id,
                actual_kms: item.actual_kms,
                billing_kms: item.billing_kms,
                rate_type_id: item.rate_type_id,
                rate_amt: item.rate_amt,
                toll_tax: item.toll_tax,
              }))
            : [
                {
                  from_destination_id: "",
                  to_destination_id: "",
                  actual_kms: "",
                  billing_kms: "",
                  rate_type_id: "",
                  rate_amt: "",
                  toll_tax: "",
                },
              ],
        }
      : undefined,
  });

  console.log("RateContactEdit", RateContactEdit);

  useEffect(() => {
    if (RateContactEdit) {
      form.reset({
        customer_id: RateContactEdit.customer_id,
        product_id: RateContactEdit.product_id,
        effective_date: RateContactEdit.effective_date,
        rate_details:
          RateContactEdit.rate_details?.map((d) => ({
            from_destination_id: d.from_destination_id,
            to_destination_id: d.to_destination_id,
            actual_kms: d.actual_kms,
            billing_kms: d.billing_kms,
            rate_type_id: d.rate_type_id,
            rate_amt: d.rate_amt,
            toll_tax: d.toll_tax,
          })) || [],
      });
    }
  }, [RateContactEdit, form]);

  // Multiple rows handler

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "rate_details",
  });

  useEffect(() => {
    const current = form.getValues("rate_details");
    if (!current || current.length === 0) {
      append({
        from_destination_id: "",
        to_destination_id: "",
        actual_kms: "",
        billing_kms: "",
        rate_type_id: "",
        rate_amt: "",
        toll_tax: "",
      });
    }
  }, []);

  // ---------------------- API SUCCESS -------------------------

  const onSuccess = (e: any, response: RateContractType) => {
    Toast.fire({
      icon: "success",
      title: "Rate contract & rate details saved",
    });
    router.push("/master/ratecontract");
  };

  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e.response?.data?.message,
    });
  };

  const saveRateContract = usePoster(
    "/ratecontract/add",
    "ratecontract",
    onSuccess,
    onError
  );

  const updateRateContract = useUpdater(
    `/ratecontract/update/${param["id"]}`,
    "updateratecontract",
    onSuccess,
    onError
  );

  // const onSubmit = (values: FormInputs) => {
  //   let payload;

  //   console.log("paramid", param["id"]);

  //   if (param["id"]) {
  //     // ⭐ UPDATE MODE
  //     payload = {
  //       ...values,
  //       modified_by: Number(loggedinuserid),
  //       modified_on: new Date(),
  //     };

  //     updateRateContract.mutate(payload);

  //     console.log("update payload", payload);
  //   } else {
  //     // ⭐ ADD MODE
  //     payload = {
  //       ...values,
  //       created_by: Number(loggedinuserid),
  //       created_on: new Date(),
  //     };

  //     saveRateContract.mutate(payload);
  //   }
  // };

const onSubmit = async (values: FormInputs) => {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4000";

  // ---------------- DUPLICATE CHECK ----------------
  for (let index = 0; index < values.rate_details.length; index++) {
    const row = values.rate_details[index];

    const customer_id = values.customer_id;
    const product_id = values.product_id;
    const effective_date = values.effective_date
      ? values.effective_date.toISOString().split("T")[0]
      : "";
    const from_id = row.from_destination_id;
    const to_id = row.to_destination_id;

    const url = `${apiBase}/ratecontract/check-duplicate?customer_id=${customer_id}&product_id=${product_id}&effective_date=${effective_date}&from_destination_id=${from_id}&to_destination_id=${to_id}`;

    console.log("Checking duplicate:", url);

    const res = await fetch(url);
    const data = await res.json();

    if (data?.exists) {
      Toast.fire({
        icon: "warning",
        title: `Row ${index + 1} already contains an existing rate detail with same customer ,date and destinations.`,
      });
      return; // ❌ STOP SUBMIT
    }
  }
  // ---------------------------------------------------

  let payload;

  if (param["id"]) {
    payload = {
      ...values,
      modified_by: Number(loggedinuserid),
      modified_on: new Date(),
    };

    updateRateContract.mutate(payload);
  } else {
    payload = {
      ...values,
      created_by: Number(loggedinuserid),
      created_on: new Date(),
    };

    saveRateContract.mutate(payload);
  }
};

  const { data: customerdropdown } = useFetcher(
      `/customer/get-customer-dropdown`,
    "customer/dropdown"
  );

  const { data: productdropdown } = useFetcher(
    `/ratecontract/get-product-dropdown`,
    "ratecontractdropdown"
  );

  const { data: ratetypedropdown } = useFetcher(
    `/ratecontract/get-ratetype-dropdown`,
    "ratetypedropdown"
  );

  const { data: fromtodestinationdropdown } = useFetcher(
    `/ratecontract/get-fromtodestination-dropdown`,
    "fromtodestinationdropdown"
  );

  useEffect(() => {
    console.log("❌ Form Errors:", form.formState.errors);
  }, [form.formState.errors]);

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="max-w-full">
        {/* MAIN MASTER FIELDS */}
        <div className="grid grid-cols-3 gap-6 mb-10">
          {/* Customer */}
          <FormField
            control={form.control}
            name="customer_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>
                  Customer <span className="text-red-500">*</span>
                </FormLabel>
                <FormControl>
                  <Select
                    value={field.value?.toString() || ""}
                    onValueChange={(value) =>
                      field.onChange(Number(value) || undefined)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select customer" />
                    </SelectTrigger>
                    <SelectContent>
                      {customerdropdown?.map((c: any) => (
                        <SelectItem
                          key={c.customer_id}
                          value={c.customer_id.toString()}
                        >
                          {c.customer_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Product */}
          <FormField
            control={form.control}
            name="product_id"
            render={({ field }) => (
              <FormItem>
                <FormLabel>
                  Product <span className="text-red-500">*</span>
                </FormLabel>
                <FormControl>
                  <Select
                    value={field.value?.toString() || ""}
                    onValueChange={(value) =>
                      field.onChange(Number(value) || undefined)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select product" />
                    </SelectTrigger>
                    <SelectContent>
                      {productdropdown?.map((p: any) => (
                        <SelectItem
                          key={p.product_id}
                          value={p.product_id.toString()}
                        >
                          {p.product_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Effective Date */}
          <FormField
            control={form.control}
            name="effective_date"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Effective Date</FormLabel>
                <FormControl>
                  <input
                    type="date"
                    value={
                      field.value
                        ? new Date(field.value).toISOString().split("T")[0]
                        : ""
                    }
                    onChange={(e) =>
                      field.onChange(
                        e.target.value ? new Date(e.target.value) : undefined
                      )
                    }
                    className="w-15 h-9 mt-10 sm:h-10 px-3 rounded-md border border-gray-300"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        {/* ---------------------- RATE DETAILS TABLE ------------------------- */}
      <div className="mt-8 w-full">
  {/* Title */}
  <div className="font-semibold mb-3 bg-gray-100 border border-gray-300 px-6 py-2 rounded">
    Add Rate Details
  </div>

  {/* Bordered Container */}
  <div className="w-full py-2 p-2">

    {/* Header Row */}
    <div className="grid grid-cols-[60px_1fr_1fr_1fr_1fr_1fr_1fr_1fr_40px] gap-4 text-sm font-medium text-gray-700 pb-2 px-1">
      <div>Sr.No</div>
      <div>From Destination <span className="text-red-500">*</span></div>
      <div>To Destination <span className="text-red-500">*</span></div>
      <div>Actual KMS <span className="text-red-500">*</span></div>
      <div>Billing KMS <span className="text-red-500">*</span></div>
      <div>Rate Type <span className="text-red-500">*</span></div>
      <div>Rate <span className="text-red-500">*</span></div>
      <div>Toll Tax</div>
      <div></div>
    </div>

    {/* Dynamic Rows */}
    {fields.map((item, index) => (
      <div
        key={item.id}
        className="grid grid-cols-[60px_1fr_1fr_1fr_1fr_1fr_1fr_1fr_40px] gap-4 mb-3 items-center px-1"
      >
        {/* S.No */}
        <div className="text-gray-700">
          {index + 1}
        </div>

        {/* From */}
        <FormField
          control={form.control}
          name={`rate_details.${index}.from_destination_id`}
          render={({ field }) => (
            <FormItem>
              <FormControl>
                <Select
                  value={field.value?.toString() || ""}
                  onValueChange={(value) =>
                    field.onChange(Number(value) || undefined)
                  }
                >
                  <SelectTrigger className="h-10">
                    <SelectValue placeholder="Select" />
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

        {/* To */}
        <FormField
          control={form.control}
          name={`rate_details.${index}.to_destination_id`}
          render={({ field }) => (
            <FormItem>
              <FormControl>
                <Select
                  value={field.value?.toString() || ""}
                  onValueChange={(value) =>
                    field.onChange(Number(value) || undefined)
                  }
                >
                  <SelectTrigger className="h-10">
                    <SelectValue placeholder="Select" />
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

        {/* Actual KMS */}
        <FormField
          control={form.control}
          name={`rate_details.${index}.actual_kms`}
          render={({ field }) => (
            <FormItem>
              <FormControl>
                <Input {...field} placeholder="0" className="h-10" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Billing KMS */}
        <FormField
          control={form.control}
          name={`rate_details.${index}.billing_kms`}
          render={({ field }) => (
            <FormItem>
              <FormControl>
                <Input {...field} placeholder="0" className="h-10" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Rate Type */}
        <FormField
          control={form.control}
          name={`rate_details.${index}.rate_type_id`}
          render={({ field }) => (
            <FormItem>
              <FormControl>
                <Select
                  value={field.value?.toString() || ""}
                  onValueChange={(value) =>
                    field.onChange(Number(value) || undefined)
                  }
                >
                  <SelectTrigger className="h-10">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent>
                    {ratetypedropdown?.map((r: any) => (
                      <SelectItem
                        key={r.rate_type_id}
                        value={r.rate_type_id.toString()}
                      >
                        {r.rate_type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Rate */}
        <FormField
          control={form.control}
          name={`rate_details.${index}.rate_amt`}
          render={({ field }) => (
            <FormItem>
              <FormControl>
                <Input {...field} placeholder="0" className="h-10" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Toll Tax */}
        <FormField
          control={form.control}
          name={`rate_details.${index}.toll_tax`}
          render={({ field }) => (
            <FormItem>
              <FormControl>
                <Input {...field} placeholder="0" className="h-10" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Delete */}
        <div className="flex items-center">
          {index > 0 && (
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
    <button
      type="button"
      onClick={() =>
        append({
          from_destination_id: "",
          to_destination_id: "",
          actual_kms: "",
          billing_kms: "",
          rate_type_id: "",
          rate_amt: "",
          toll_tax: "",
        })
      }
      className="text-blue-600 font-medium mt-2 px-1"
    >
      + Add
    </button>
  </div>
</div>


        {/* ---------------------- BUTTONS ------------------------- */}

        <div className="fixed bottom-6 right-6 flex gap-4 z-50">
          <Button type="submit" className="bg-green-700 text-white px-6">
            Save
          </Button>
          <Button
        type="button"
        className="border-red-500"
        onClick={() => router.push("/master/ratecontract")}
        variant="outline"
      >
        Cancel
      </Button>
        </div>
      </form>
    </Form>
  );
}
