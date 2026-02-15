"use client";

import React, { useEffect, useState } from "react";
import { ChevronRight } from "lucide-react";
import * as z from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { driverBasicSchema, DriverInfoSchema } from "@/schemas/driver-schema";
import { DriverInfo } from "@/types/driver-type";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Cookies from "js-cookie";
import Toast from "@/components/shared/toast";
import {
  useDeleter,
  usePoster,
  usePosterWithFileUpload,
  useUpdater,
} from "@/hooks/use-query";
import { useQueryClient } from "@tanstack/react-query";

type DriverInfoFormProps = {
  driverId?: number | null
  driverinfo?: DriverInfo;
  initialData?: any;
  mode?: "add" | "edit" | "view";
  onChange: (data: any) => void;
  onNext?: () => void;
  readOnly?: boolean;
};

type FormInputs = z.infer<typeof DriverInfoSchema>;

const DriverInfoForm = ({
  driverId,
  driverinfo,
  initialData = {},
  mode = "add",
  onChange,
  onNext,
  readOnly = false,
}: DriverInfoFormProps) => {
  const param = useParams();
  const router = useRouter();
  const [loggedincompanyid] = useState(Cookies.get("loggedincompanyid"));
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));

  const detectedMode = driverinfo?.driver_info_id ? "edit" : "add";
  const searchParams = useSearchParams();
  const routeDriverId =
    Number(searchParams.get("driver_id")) ||
    Number(localStorage.getItem("driver_id"));

  const form = useForm<FormInputs>({
    resolver: zodResolver(DriverInfoSchema),
    defaultValues: initialData,
  });

  useEffect(() => {
    if (initialData) {
      form.reset(initialData);
    }
  }, [initialData]);

  const queryClient = useQueryClient();

  // Replace the entire onSuccess function
  const onSuccess = (response: any) => {
    const updatedInfo = response[0];

    Toast.fire({
      icon: "success",
      title:
        detectedMode === "edit"
          ? "Driver Information updated successfully"
          : "Driver Information added successfully",
    });

    // Invalidate query to refetch data
    queryClient.invalidateQueries({
      queryKey: ["driverfullbyid"],
    });

    // Save driver_id only on ADD
    if (mode === "add") {
      const driverId = response?.driver_id;
      if (driverId) {
        localStorage.setItem("driver_id", driverId.toString());
      }
    }

    // Reset form with updated values
    if (detectedMode === "edit") {
      form.reset({
        ...form.getValues(),
        ...updatedInfo,
      });
    }

    if (onNext) onNext();
  };

  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e?.response?.data?.message || "Submission Failed",
    });
  };

  const addDriverInfo = usePoster(
    "/driver/add-driver-info",
    "AddDriverInfo",
    onSuccess,
    onError
  );

  const updateDriverInfo = useUpdater(
    `/driver/update-driver-info/${driverinfo?.driver_info_id || param["id"]}`,
    "driverinfobyid",
    onSuccess,
    onError
  );

  const onSubmit = (values: any) => {
    try {
      console.log("Form values:", values);
      console.log("Driverinfo prop:", driverinfo);
      console.log("Mode:", mode);

      // ✅ FIX: Use param["id"] in edit mode, localStorage only for add mode
      const driverId =
        detectedMode === "edit"
          ? Number(param["id"])
          : Number(searchParams.get("driver_id")) ||
            Number(localStorage.getItem("driver_id"));

      // Helper function to convert date strings to ISO format
      const toISODateTime = (dateStr: string) => {
        if (!dateStr || dateStr.trim() === "") return null;
        return new Date(dateStr).toISOString();
      };

      // Convert date fields to ISO format
      const cleanValues = {
        ...values,
        last_emp_date: toISODateTime(values.last_emp_date),
        leaving_date: toISODateTime(values.leaving_date),
      };

      const infoData = {
        ...cleanValues,
        driver_id: driverId,
        status: "Active",
      };

      // ✅ Add driver_info_id for UPDATE
      if (detectedMode === "edit") {
        const driverInfoId =
          driverinfo?.driver_info_id ||
          initialData?.driver_info_id ||
          values?.driver_info_id;

        if (!driverInfoId) {
          console.error("Missing driver_info_id. Available data:", {
            driverinfo,
            initialData,
            values,
          });
          Toast.fire({
            icon: "error",
            title: "driver_info_id is missing. Cannot update.",
          });
          return;
        }

        infoData.driver_info_id = driverInfoId;

        // ✅ Use modified_on and modified_by (not updated_by/updated_on)
        infoData.modified_by = Number(loggedinuserid);
        infoData.modified_on = new Date().toISOString();

        // ✅ Remove fields not allowed in UPDATE
        delete infoData.created_by;
        delete infoData.created_on;
        delete infoData.updated_by;
        delete infoData.updated_on;
        delete infoData.status_updatedby;
        delete infoData.status_updatedon;
      } else {
        // Only set created_by/created_on for NEW info
        infoData.created_by = Number(loggedinuserid);
        infoData.created_on = new Date().toISOString();
        infoData.status = "Active";
      }

      console.log("🔍 Final payload:", {
        driver_id: driverId,
        info: [infoData],
      });

      // ✅ Call correct mutation based on mode
      if (detectedMode === "edit") {
        updateDriverInfo.mutate({
          driver_id: driverId,
          info: [infoData],
        });
      } else {
        addDriverInfo.mutate({
          driver_id: driverId,
          info: [infoData],
        });
      }
    } catch (error) {
      console.log(error);
    }
  };

  const isReadOnly = readOnly || mode === "view";

  useEffect(() => {
    console.log(form.formState.errors);
  }, [form.formState.errors]);

  return (
    <div className="w-full px-6 py-4">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <div className="space-y-5">
            {/* Emergency Contact Information */}
            <div className="border-b pb-4">
              <h3 className="text-lg font-medium text-gray-800 mb-4">
                Emergency Contact Information
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField
                  control={form.control}
                  name="to_inform_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Contact Person Name</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Enter name" className="w-72"/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="to_inform_mobile_no"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Mobile Number</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Enter mobile number" className="w-72"/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="to_inform_address"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Address</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Enter address" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="to_inform_relationship"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Relationship</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Enter relationship" className="w-72"/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Employment History */}
            <div className="border-b pb-4">
              <h3 className="text-lg font-medium text-gray-800 mb-4">
                Employment History
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <FormField
                  control={form.control}
                  name="past_history"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Past History</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Enter past history" className="w-72"/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="past_emp"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Past Employment</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Enter past employment" className="w-72"/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="past_emp_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Past Employer Name</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Enter employer name" className="w-72"/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="last_emp_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Last Employment Date</FormLabel>
                      <FormControl>
                        <Input {...field} type="date" className="w-36"/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="last_emp_address"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Last Employer Address</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="Enter employer address"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="last_emp_mobile"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Last Employer Mobile No.</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="Enter Mobile number"
                          className="w-72"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="reason_leaving_job"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Reason for Leaving Job</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Enter reason" className="w-72"/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="leaving_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Leaving Date</FormLabel>
                      <FormControl>
                        <Input {...field} type="date" className="w-36"/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Accident Information */}
            <div className="border-b pb-4">
              <h3 className="text-lg font-medium text-gray-800 mb-4">
                Accident Information
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField
                  control={form.control}
                  name="nature_of_accident"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Nature of Accident</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="Enter nature of accident"
                          className="w-72"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="location_of_accident"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Location of Accident</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Enter location" className="w-72"/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="driver_fatalities"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Driver Fatalities</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="Enter number of fatalities"
                          className="w-72"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="driver_injury"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Driver Injury</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Enter injury details" className="w-72"/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Introducer Information */}
            <div className="border-b pb-4">
              <h3 className="text-lg font-medium text-gray-800 mb-4">
                Introducer Information
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField
                  control={form.control}
                  name="introducer_driver_code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Introducer Driver Code</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Enter driver code" className="w-72"/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="introducer_driver_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Introducer Driver Name</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Enter driver name" className="w-72"/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="introducer_driver_address"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Introducer Driver Address</FormLabel>
                      <FormControl>
                        <Input {...field} placeholder="Enter address" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="introducer_driver_mobile"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Introducer Driver Mobile No.</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="Enter telephone number"
                          className="w-72"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Next Button */}
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            {!isReadOnly && (
              <Button
                type="submit"
                disabled={addDriverInfo.isLoading || updateDriverInfo.isLoading}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white"
              >
                {addDriverInfo.isLoading || updateDriverInfo.isLoading
                  ? "Saving..."
                  : detectedMode === "edit"
                  ? "Update Information"
                  : "Save Information"}
              </Button>
            )}
          </div>
        </form>
      </Form>
    </div>
  );
};

export default DriverInfoForm;
