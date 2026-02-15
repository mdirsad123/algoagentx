"use client";
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import React, { useEffect } from "react";
import { UseFormReturn } from "react-hook-form";
import { z } from "zod";
import { VehicleSchema } from "@/schemas/vehicle-schema";

type FormInputs = z.infer<typeof VehicleSchema>;

type VehicleFormProps = {
  form: UseFormReturn<FormInputs>;
  asDialog?: boolean;
  readOnly?: boolean;
};

const InvoiceVehicleForm = ({ form, readOnly }: VehicleFormProps) => {
  // 🔹 Safe Number Handler
  const handleNumberChange = (field: any, value: string) => {
    if (value === "") return field.onChange(null);
    const num = Number(value);
    if (!isNaN(num)) field.onChange(num);
  };


   useEffect(() => {       //
          console.log(form.formState.errors);
        }, [form.formState.errors]);
  
  return (
    <>
    <div className={readOnly ? "pointer-events-none text-opacity-80 p-3" : ""}>
      <div className="grid lg:grid-cols-[250px_160px_190px] md:grid-cols-3 gap-6 mb-6">
        <FormField
          control={form.control}
          name="inv_no"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-sm font-medium text-gray-700">
                Invoice no.
              </FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  placeholder="Enter Invoice no."
                  className="h-9"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="inv_date"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-sm font-medium text-gray-700">
                Invoice date
              </FormLabel>
              <FormControl>
                <input
                  type="date"
                  value={
                    field.value
                      ? new Date(field.value).toISOString().split("T")[0]
                      : ""
                  }
                  onChange={(e) => field.onChange(e.target.value)}
                  className="w-full h-9 px-2 border border-gray-300 rounded-md"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="inv_amt"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-sm font-medium text-gray-700">
                Invoice amount
              </FormLabel>
              <FormControl>
                <Input
                  type="number"
                  value={field.value ?? ""}
                  onChange={(e) =>
                    handleNumberChange(field, e.target.value)
                  }
                  placeholder="Enter Invoice amount"
                  className="h-9"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>

      <div className="grid lg:grid-cols-[250px_160px_190px] md:grid-cols-3 gap-6 mb-6">
        <FormField
          control={form.control}
          name="tank_no"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-sm font-medium text-gray-700">
                Tank/cont.no
              </FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  placeholder="Enter Tank/cont.no"
                  className="h-9"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="sale_date"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-sm font-medium text-gray-700">
                Sale Date
              </FormLabel>
              <FormControl>
                <input
                  type="date"
                  value={
                    field.value
                      ? new Date(field.value).toISOString().split("T")[0]
                      : ""
                  }
                  onChange={(e) => field.onChange(e.target.value)}
                  className="w-full h-9 px-2 border border-gray-300 rounded-md"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
         <FormField
          control={form.control}
          name="sale_of_vehicle"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-sm font-medium text-gray-700">
                Sales of vehicle
              </FormLabel>
              <FormControl>
                <Input
                  type="number"
                   value={field.value ?? ""}
                  onChange={(e) =>
                    handleNumberChange(field, e.target.value)
                  }
                  placeholder="Enter Sales of vehicle"
                  className="h-9"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>
    </div>
    </>
  );
};

export default InvoiceVehicleForm;
