"use client";
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import React, { useEffect, useState } from "react";
import { UseFormReturn } from "react-hook-form";
import { z } from "zod";
import { VehicleSchema } from "@/schemas/vehicle-schema";
import { useFetcher } from "@/hooks/use-query";
import {
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";

type FormInputs = z.infer<typeof VehicleSchema>;

type VehicleFormProps = {
  form: UseFormReturn<FormInputs>;
  asDialog?: boolean;
  readOnly?: boolean;
  existingFiles?: {
    invoice_document?: string | null;
    rc_document?: string | null;
    insurance_document?: string | null;
  };
  setShowMakeForm: (value: boolean) => void;
};

const VehicleForm = ({ form ,existingFiles,readOnly,setShowMakeForm}: VehicleFormProps) => {

  // const [showMakeForm, setShowMakeForm] = useState(false);

  // 🔹 Safe Number Handler (Prevents NaN)
  const handleNumberChange = (field: any, value: string) => {
    if (value === "") return field.onChange(null);
    const num = Number(value);
    if (!isNaN(num)) field.onChange(num);
  };

  const { data: VehicleMakeList } = useFetcher(
  "/vehicle/vehiclemakelist",
  "vehiclemakelist"
);


 useEffect(() => {       //
        console.log(form.formState.errors);
      }, [form.formState.errors]);


  return (
  <div className="p-3 space-y-6 dark:text-gray-200">

    {/* <div className="space-y-6"> */}
      <h2 className="font-semibold text-lg text-gray-800 dark:text-gray-100 border-b pb-2">
        Vehicle Details
      </h2>
      <div className={readOnly ? "pointer-events-none text-opacity-80" : ""}>
        <div className="space-y-6">

      <div className="grid lg:grid-cols-4 md:grid-cols-3 gap-6">

        <FormField
          control={form.control}
          name="vehicle_no"
          render={({ field }) => (
            <FormItem >
              <FormLabel className="text-gray-800">Vehicle No.<span className="text-red-500">*</span></FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  placeholder="Enter Vehicle No"
                  className="h-9 dark:bg-gray-800"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

      <FormField
        control={form.control}
        name="make_id"
        render={({ field }) => (
          <FormItem>
            <FormLabel className="text-gray-800">
              Vehicle Make <span className="text-red-500">*</span>
            </FormLabel>

            <div className="flex items-center gap-2">
              <FormControl className="flex-1">
                <Select value={field.value ?? ""} onValueChange={field.onChange}>
                  <SelectTrigger className="h-9 dark:bg-gray-800">
                    <SelectValue placeholder="Select Vehicle" />
                  </SelectTrigger>
                  <SelectContent className="dark:bg-gray-900">
                    {VehicleMakeList?.map(({ make_id, vehicle_name }: any, i: number) => (
                      <SelectItem
                        key={`${make_id}${i}`}
                        value={String(make_id)}
                        className="dark:text-gray-200"
                      >
                        {vehicle_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormControl>

              {!readOnly && (
              <Button
                type="button"
                size="sm"
                className="bg-blue-600 text-white"
                onClick={() => setShowMakeForm(true)}
              >
                + Add
              </Button>
              )}
            </div>

            <FormMessage />
          </FormItem>
        )}
      />



        <FormField
          control={form.control}
          name="vehicle_model"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Vehicle Model</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  placeholder="Enter Model"
                  className="h-9 dark:bg-gray-800"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        
      </div>

      <div className="grid lg:grid-cols-4 md:grid-cols-3 gap-6">
        <FormField
          control={form.control}
          name="year_mfg"
          render={({ field }) => {
            const currentYear = new Date().getFullYear();
            const years = Array.from({ length: currentYear - 1949 }, (_, i) => currentYear - i);

            return (
              <FormItem>
                <FormLabel>Year of Manufacturing</FormLabel>
                <Select
                  value={
                    field.value
                      ? new Date(field.value).getFullYear().toString()
                      : ""
                  }
                  onValueChange={(year) => field.onChange(`${year}-01-01`)}
                >
                  <SelectTrigger className="h-9 w-full dark:bg-gray-800 dark:text-gray-200">
                    <SelectValue placeholder="Select Year" />
                  </SelectTrigger>

                  <SelectContent className="dark:bg-gray-900 dark:text-gray-200 max-h-60">
                    {years.map((year) => (
                      <SelectItem
                        key={year}
                        value={year.toString()}
                        className="dark:text-gray-200"
                      >
                        {year}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            );
          }}
        />

        <FormField
          control={form.control}
          name="chassis_no"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Chassis No</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  placeholder="Enter Chassis No"
                  className="h-9 dark:bg-gray-800"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="engine_no"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Engine No</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  placeholder="Enter Engine No"
                  className="h-9 dark:bg-gray-800"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="dealer_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Dealer Name</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  className="h-9 dark:bg-gray-800"
                  placeholder="Enter Dealer Name"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

      </div>

        <FormField
          control={form.control}
          name="purchase_hire"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Purchase / Hire</FormLabel>
              <div className="flex gap-6 mt-2">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    value="Purchase"
                    checked={field.value === "Purchase"}
                    onChange={(e) => field.onChange(e.target.value)}
                    className="accent-blue-600"
                  />
                  Purchase
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    value="Hire"
                    checked={field.value === "Hire"}
                    onChange={(e) => field.onChange(e.target.value)}
                    className="accent-blue-600"
                  />
                  Hire
                </label>
              </div>
              <FormMessage />
            </FormItem>
          )}
        />

     
      <div className="grid lg:grid-cols-4 md:grid-cols-3 gap-6">

        <FormField
          control={form.control}
          name="purchase_inv_no"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Purchase Invoice No.</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  placeholder="Enter Invoice No"
                  className="h-9 dark:bg-gray-800"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="purchase_inv_amt"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Purchase Invoice Amount</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  value={field.value ?? ""}
                  onChange={(e) => handleNumberChange(field, e.target.value)}
                  placeholder="Enter Amount"
                  className="h-9 dark:bg-gray-800"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="purchase_inv_date"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Purchase Invoice Date</FormLabel>
              <FormControl>
                <input
                  type="date"
                  value={field.value ? new Date(field.value).toISOString().split("T")[0] : ""}
                  onChange={(e) => field.onChange(e.target.value)}
                  className="h-9 w-full border rounded-md px-2 dark:bg-gray-800"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>

      <div className="grid lg:grid-cols-4 md:grid-cols-3 gap-6">

        <FormField
          control={form.control}
          name="cabin_fab_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Cabin Fabricator Name</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  placeholder="Enter Fabricator"
                  className="h-9 dark:bg-gray-800"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="cabin_inv_no"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Cabin Invoice No.</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  placeholder="Enter Invoice No"
                  className="h-9 dark:bg-gray-800"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="cabin_inv_date"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Cabin Invoice Date</FormLabel>
              <FormControl>
                <input
                  type="date"
                  value={field.value ? new Date(field.value).toISOString().split("T")[0] : ""}
                  onChange={(e) => field.onChange(e.target.value)}
                  className="h-9 w-full border rounded-md px-2 dark:bg-gray-800"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

      <FormField
        control={form.control}
        name="cabin_fab_amt"
        render={({ field }) => (
          <FormItem className="w-full">
            <FormLabel>Cabin Fabrication Amount</FormLabel>
            <FormControl>
              <Input
                type="number"
                value={field.value ?? ""}
                onChange={(e) => handleNumberChange(field, e.target.value)}
                placeholder="Enter Amount"
                className="h-9 dark:bg-gray-800"
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      </div>
     
      <div className="grid lg:grid-cols-4 md:grid-cols-3 gap-6">

        <FormField
          control={form.control}
          name="running_gear_fab_by"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Running Gear Fabricator</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  placeholder="Enter Fabricator"
                  className="h-9 dark:bg-gray-800"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="running_gear_inv_no"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Running Gear Invoice No.</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  placeholder="Enter Invoice No"
                  className="h-9 dark:bg-gray-800"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="running_gear_inv_date"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Running Gear Invoice Date</FormLabel>
              <FormControl>
                <input
                  type="date"
                  value={field.value ? new Date(field.value).toISOString().split("T")[0] : ""}
                  onChange={(e) => field.onChange(e.target.value)}
                  className="h-9 w-full border rounded-md px-2 dark:bg-gray-800"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

      <FormField
        control={form.control}
        name="running_gear_fab_amt"
        render={({ field }) => (
          <FormItem className="w-full">
            <FormLabel>Running Gear Fabrication Amount</FormLabel>
            <FormControl>
              <Input
                type="number"
                value={field.value ?? ""}
                onChange={(e) => handleNumberChange(field, e.target.value)}
                placeholder="Enter Amount"
                className="h-9 dark:bg-gray-800"
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />
      </div>

      <div className="space-y-6">
        <h2 className="font-semibold text-lg text-gray-800 dark:text-gray-100 border-b pb-2">
          Insurance Details
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">

          <FormField
            control={form.control}
            name="policy_no"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Policy No</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    value={field.value ?? ""}
                    placeholder="Enter Policy No"
                    className="h-9 dark:bg-gray-800"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="policy_date"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Policy Date</FormLabel>
                <FormControl>
                  <input
                    type="date"
                    value={field.value ? new Date(field.value).toISOString().split("T")[0] : ""}
                    onChange={(e) => field.onChange(e.target.value)}
                    className="h-9 w-full border rounded-md px-2 dark:bg-gray-800"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="policy_amount"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Policy Amount</FormLabel>
                <FormControl>
                  <Input
                    type="number"
                    value={field.value ?? ""}
                    onChange={(e) => handleNumberChange(field, e.target.value)}
                    className="h-9 dark:bg-gray-800"
                    placeholder="Enter Policy Amount"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="policy_expiry"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Expiry Date</FormLabel>
                <FormControl>
                  <input
                    type="date"
                    value={field.value ? new Date(field.value).toISOString().split("T")[0] : ""}
                    onChange={(e) => field.onChange(e.target.value)}
                    className="h-9 w-full border rounded-md px-2 dark:bg-gray-800"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

        </div>
      </div>
      </div>
      </div>
    </div>
  // </div>
);

};

export default VehicleForm;
