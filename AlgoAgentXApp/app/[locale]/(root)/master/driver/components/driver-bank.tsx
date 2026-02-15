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
import React, { useEffect, useState, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Toast from "@/components/shared/toast";
import { cn } from "@/lib/utils";
import { useDeleter, usePoster, useUpdater } from "@/hooks/use-query";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Cookies from "js-cookie";
import { useTranslation } from "@/hooks/use-translations";
import { DriverBankSchema } from "@/schemas/driver-schema";
import { DriverBank } from "@/types/driver-type";
import { useQueryClient } from "@tanstack/react-query";

type DriverBankFormProps = {
  driverId?: number | null,
  driverbank?: DriverBank;
  initialData?: any;
  mode?: "add" | "edit" | "view";
  readOnly?: boolean;
  onSuccess?: () => void;
  onNext?: (data: any) => void;
};

type FormInputs = z.infer<typeof DriverBankSchema>;

const DriverBankForm = ({
  driverId,
  driverbank,
  initialData = {},
  mode = "add",
  readOnly = false,
  onSuccess: onSuccessCallback,
}: DriverBankFormProps) => {
  const { t, isRTL, locale } = useTranslation();
  const param = useParams();
  const router = useRouter();
  const isInitialized = useRef(false);
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));

  const detectedMode = driverbank?.driver_bank_id ? "edit" : "add";

  const searchParams = useSearchParams();
  const routeDriverId =
    Number(searchParams.get("driver_id")) ||
    Number(localStorage.getItem("driver_id"));

  const form = useForm<FormInputs>({
    resolver: zodResolver(DriverBankSchema),
    defaultValues: {
      driver_bank_acc_no: initialData?.driver_bank_acc_no || "",
      driver_bank_branch_name: initialData?.driver_bank_branch_name || "",
      driver_bank_name: initialData?.driver_bank_name || "",
      driver_bank_address: initialData?.driver_bank_address || "",
      driver_ifsc_code: initialData?.driver_ifsc_code || "",
      driver_micr_no: initialData?.driver_micr_no || "",
      driver_accident_date: initialData?.driver_accident_date || "",
    },
  });

  useEffect(() => {
    if (initialData) {
      form.reset(initialData);
    }
  }, [initialData]);

  const queryClient = useQueryClient();

  const INDIAN_BANKS = [
    "State Bank of India (SBI)",
    "HDFC Bank",
    "ICICI Bank",
    "Axis Bank",
    "Kotak Mahindra Bank",
    "Punjab National Bank (PNB)",
    "Bank of Baroda",
    "Canara Bank",
    "Union Bank of India",
    "Indian Bank",
    "IDBI Bank",
    "IDFC First Bank",
    "IndusInd Bank",
    "Yes Bank",
    "Federal Bank",
    "Bank of India",
    "Central Bank of India",
    "UCO Bank",
    "Bank of Maharashtra",
    "South Indian Bank",
    "Bandhan Bank",
    "RBL Bank",
    "Other",
  ];

  // Replace onSuccess function
  const onSuccess = (response: any) => {
    const updatedBank = response[0];

    Toast.fire({
      icon: "success",
      title:
        detectedMode === "edit"
          ? "Driver Bank updated successfully"
          : "Driver Bank added successfully",
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
        ...updatedBank,
      });
    }

    // Navigate to master page or call onNext

    router.push("/master/driver");
  };

  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e?.response?.data?.message || "Submission Failed",
    });
  };

  const addDriverBank = usePoster(
    "/driver/add-driver-bank",
    "AddDriverInfo",
    onSuccess,
    onError
  );

  const updateDriverBank = useUpdater(
    `/driver/update-driver-bank/${driverbank?.driver_bank_id || param["id"]}`,
    "driverbyid",
    onSuccess,
    onError
  );

  const onSubmit = (values: any) => {
    // ✅ FIX: Use param["id"] in edit mode, localStorage only for add mode
    const driverId =
      detectedMode === "edit"
        ? Number(param["id"])
        : Number(searchParams.get("driver_id")) ||
          Number(localStorage.getItem("driver_id"));

    if (!driverId) {
      Toast.fire({
        icon: "error",
        title: "Driver ID not found. Please complete the first tab.",
      });
      return;
    }

    // Convert date to ISO if user selected it from date input
    const accidentDate = values.driver_accident_date
      ? new Date(values.driver_accident_date).toISOString()
      : null;

    const bankData = {
      ...values,
      driver_accident_date: accidentDate,
      driver_id: driverId,
      status: "Active",
    };

    // ✅ Add driver_bank_id for UPDATE
    if (detectedMode === "edit") {
      const driverBankId =
        driverbank?.driver_bank_id || initialData?.driver_bank_id;

      if (!driverBankId) {
        console.error("Missing driver_bank_id. Available data:", {
          driverbank,
          initialData,
        });
        Toast.fire({
          icon: "error",
          title: "driver_bank_id is missing. Cannot update.",
        });
        return;
      }

      bankData.driver_bank_id = driverBankId;
      bankData.modified_by = Number(loggedinuserid);
      bankData.modified_on = new Date().toISOString();

      // Remove fields not allowed in UPDATE (Prisma relations)
      delete bankData.created_by;
      delete bankData.created_on;
    } else {
      // Only set created_by/created_on for NEW bank
      bankData.created_by = Number(loggedinuserid);
      bankData.created_on = new Date().toISOString();
    }

    const payload = {
      driver_id: driverId,
      bank: [bankData], // ✅ Must be array for backend's bank.map()
    };

    console.log("🔍 Final payload:", payload);

    // ✅ Call correct mutation based on mode
    if (detectedMode === "edit") {
      updateDriverBank.mutate(payload);
    } else {
      addDriverBank.mutate(payload);
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
          <div>
            {/* Bank Details Section */}
            <div className="mb-8">
              <h2 className="text-base font-medium text-gray-900 dark:text-gray-100 mb-6">
                Bank Details
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Bank Account No. */}
                <FormField
                  control={form.control}
                  name="driver_bank_acc_no"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        Bank Account No.
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Bank Account No."
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm bg-white dark:bg-gray-900"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Bank Branch */}
                <FormField
                  control={form.control}
                  name="driver_bank_branch_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        Bank Branch
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Bank Branch"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm bg-white dark:bg-gray-900"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Bank Name */}
                <FormField
                  control={form.control}
                  name="driver_bank_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        Bank Name
                      </FormLabel>
                      <FormControl>
                        <Select
                          onValueChange={field.onChange}
                          value={field.value}
                        >
                          <FormControl>
                            <SelectTrigger className="w-72">
                              <SelectValue placeholder="Select Bank" />
                            </SelectTrigger>
                          </FormControl>

                          <SelectContent>
                            <SelectItem value="none">Select Bank</SelectItem>
                            {INDIAN_BANKS.map((bank) => (
                              <SelectItem key={bank} value={bank}>
                                {bank}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Bank Address */}
                <FormField
                  control={form.control}
                  name="driver_bank_address"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        Bank Address
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Bank Address"
                          {...field}
                          readOnly={isReadOnly}
                          className="h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm bg-white dark:bg-gray-900"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* IFSC Code */}
                <FormField
                  control={form.control}
                  name="driver_ifsc_code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        IFSC Code
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter IFSC Code"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm bg-white dark:bg-gray-900"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* MICR No. */}
                <FormField
                  control={form.control}
                  name="driver_micr_no"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        MICR No.
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter MICR No."
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm bg-white dark:bg-gray-900"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Accident Details Section */}
            <div className="mb-8">
              <h2 className="text-base font-medium text-gray-900 dark:text-gray-100 mb-6">
                Accident Details
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Accident Date */}
                <FormField
                  control={form.control}
                  name="driver_accident_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        Accident Date
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="date"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-36 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm bg-white dark:bg-gray-900"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              {!isReadOnly && (
                <Button
                  type="submit"
                  disabled={
                    addDriverBank.isLoading || updateDriverBank.isLoading
                  }
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white"
                >
                  {addDriverBank.isLoading || updateDriverBank.isLoading
                    ? "Saving..."
                    : detectedMode === "edit"
                    ? "Update Bank"
                    : "Save Bank"}
                </Button>
              )}
            </div>
          </div>
        </form>
      </Form>
    </div>
  );
};

export default DriverBankForm;
