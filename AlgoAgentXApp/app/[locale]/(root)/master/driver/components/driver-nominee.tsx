"use client";

import React, { useEffect, useState } from "react";
import { ChevronRight, FileText, Paperclip, Plus, X } from "lucide-react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import * as z from "zod";
import Cookies from "js-cookie";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";
import { DriverNominee } from "@/types/driver-type";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DriverNomineeSchema } from "@/schemas/driver-schema";
import {
  useDeleter,
  usePosterWithFileUpload,
  useUpdater,
  useUpdaterWithFileUpload,
} from "@/hooks/use-query";
import Toast from "@/components/shared/toast";
import { useQueryClient } from "@tanstack/react-query";

type DriverNomineeFormProps = {
  drivernominee?: DriverNominee;
  nominees?: any;
  initialData?: any;
  mode?: "add" | "edit" | "view";
  onChange: (data: any) => void;
  onNext?: () => void;
  readOnly?: boolean;
};

type FormInputs = z.infer<typeof DriverNomineeSchema>;

const DriverNomineeForm = ({
  drivernominee,
  nominees,
  initialData = {},
  mode = "add",
  onNext,
  readOnly = false,
}: DriverNomineeFormProps) => {
  const param = useParams();
  const router = useRouter();
  const [loggedincompanyid] = useState(Cookies.get("loggedincompanyid"));
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));

  const form = useForm<FormInputs>({
    resolver: zodResolver(DriverNomineeSchema),
    defaultValues: {
      nominees: initialData?.nominees?.length
        ? initialData.nominees.map((n: any) => ({
            nominee_id: n.nominee_id,
            relation: n.relation || "",
            name: n.name || "",
            aadhaar_no: n.aadhaar_no || "",
            aadhaar_doc: n.aadhaar_doc || "",
            mobile_no: n.mobile_no || "",
          }))
        : [
            {
              relation: "",
              name: "",
              aadhaar_no: "",
              aadhaar_doc: "",
              mobile_no: "",
            },
          ],
    },
  });

  useEffect(() => {
    if (initialData?.nominees?.length) {
      form.reset({
        nominees: initialData.nominees.map((n: any) => ({
          nominee_id: n.nominee_id,
          relation: n.relation || "",
          name: n.name || "",
          aadhaar_no: n.aadhaar_no || "",
          aadhaar_doc: n.aadhaar_doc || "",
          mobile_no: n.mobile_no || "",
        })),
      });
    } else {
      // ✅ Ensure at least one empty nominee field exists
      form.reset({
        nominees: [
          {
            relation: "",
            name: "",
            aadhaar_no: "",
            aadhaar_doc: "",
            mobile_no: "",
          },
        ],
      });
    }
  }, [initialData, form]);

  const searchParams = useSearchParams();
  const driverId =
    Number(searchParams.get("driver_id")) ||
    Number(localStorage.getItem("driver_id"));

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "nominees",
  });

  const queryClient = useQueryClient();

  const onSuccess = (response: any) => {
    Toast.fire({
      icon: "success",
      title:
        mode === "edit"
          ? "Driver Nominee updated successfully"
          : "Driver Nominee added successfully",
    });

    // ✅ Invalidate query to refetch data
    queryClient.invalidateQueries({
      queryKey: ["driverfullbyid"],
    });

    // ✅ Reset form with updated values from response
    if (response && Array.isArray(response)) {
      form.reset({
        nominees: response.map((n: any) => ({
          nominee_id: n.nominee_id,
          relation: n.relation || "",
          name: n.name || "",
          aadhaar_no: n.aadhaar_no || "",
          aadhaar_doc: n.aadhaar_doc || "",
          mobile_no: n.mobile_no || "",
        })),
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

  const addDriverNominees = usePosterWithFileUpload(
    "/driver/add-driver-nominees",
    "AddDriverNominees",
    onSuccess,
    onError
  );

  const updateDriverNominees = useUpdaterWithFileUpload(
    `/driver/update-driver-nominees/${driverId}`,
    "UpdateDriverNominees",
    onSuccess,
    onError
  );

  // const onSubmit = (values: any) => {
  //   const formData = new FormData();

  //   console.log("📤 Submitting nominees:", values.nominees);

  //   // Required for FK
  //   formData.append("driver_id", String(driverId));

  //   // 🔥 Append nominees data directly
  //   values.nominees.forEach((nominee: any, index: number) => {
  //     // Add nominee_id if exists (for updates)
  //     if (nominee.nominee_id) {
  //       formData.append(
  //         `nominees[${index}][nominee_id]`,
  //         String(nominee.nominee_id)
  //       );
  //     }

  //     formData.append(`nominees[${index}][relation]`, nominee.relation || "");
  //     formData.append(`nominees[${index}][name]`, nominee.name || "");
  //     formData.append(`nominees[${index}][mobile_no]`, nominee.mobile_no || "");
  //     formData.append(
  //       `nominees[${index}][aadhaar_no]`,
  //       nominee.aadhaar_no || ""
  //     );
  //     formData.append(`nominees[${index}][status]`, "Active");
  //     formData.append(`nominees[${index}][created_by]`, String(loggedinuserid));
  //     formData.append(
  //       `nominees[${index}][created_on]`,
  //       new Date().toISOString()
  //     );

  //     // ✅ Handle file uploads
  //     if (nominee.aadhaar_doc instanceof File) {
  //       formData.append("files", nominee.aadhaar_doc);
  //       formData.append(`nominees[${index}][aadhaar_doc]`, "null"); // Mark for backend replacement
  //     } else if (
  //       nominee.aadhaar_doc &&
  //       typeof nominee.aadhaar_doc === "string"
  //     ) {
  //       formData.append(`nominees[${index}][aadhaar_doc]`, nominee.aadhaar_doc);
  //     } else {
  //       formData.append(`nominees[${index}][aadhaar_doc]`, "");
  //     }

  //     // Add modified fields if in edit mode
  //     if (mode === "edit") {
  //       formData.append(
  //         `nominees[${index}][modified_by]`,
  //         String(loggedinuserid)
  //       );
  //       formData.append(
  //         `nominees[${index}][modified_on]`,
  //         new Date().toISOString()
  //       );
  //     }
  //   });

  //   // Use update if in edit mode and nominees exist, otherwise add
  //   if (mode === "edit" || initialData?.nominees?.length > 0) {
  //     updateDriverNominees.mutate(formData);
  //   } else {
  //     addDriverNominees.mutate(formData);
  //   }
  // };

  const RELATIONS = [
    "Father",
    "Mother",
    "Husband",
    "Wife",
    "Spouse",
    "Son",
    "Daughter",
    "Brother",
    "Sister",
    "Grandfather",
    "Grandmother",
    "Uncle",
    "Aunt",
    "Cousin",
    "Guardian",
    "Friend",
    "Other",
  ];

  const onSubmit = (values: any) => {
    const formData = new FormData();

    console.log("📤 Submitting nominees:", values.nominees);

    // Required for FK
    formData.append("driver_id", String(driverId));

    // 🔥 Append nominees data directly
    values.nominees.forEach((nominee: any, index: number) => {
      // Add nominee_id if exists (for updates)
      if (nominee.nominee_id) {
        formData.append(
          `nominees[${index}][nominee_id]`,
          String(nominee.nominee_id)
        );
      }

      formData.append(`nominees[${index}][relation]`, nominee.relation || "");
      formData.append(`nominees[${index}][name]`, nominee.name || "");
      formData.append(`nominees[${index}][mobile_no]`, nominee.mobile_no || "");
      formData.append(
        `nominees[${index}][aadhaar_no]`,
        nominee.aadhaar_no || ""
      );
      formData.append(`nominees[${index}][status]`, "Active");
      formData.append(`nominees[${index}][created_by]`, String(loggedinuserid));
      formData.append(
        `nominees[${index}][created_on]`,
        new Date().toISOString()
      );

      // ✅ Handle file uploads
      if (nominee.aadhaar_doc instanceof File) {
        formData.append("files", nominee.aadhaar_doc);
        formData.append(`nominees[${index}][aadhaar_doc]`, "null");
      } else if (
        nominee.aadhaar_doc &&
        typeof nominee.aadhaar_doc === "string"
      ) {
        formData.append(`nominees[${index}][aadhaar_doc]`, nominee.aadhaar_doc);
      } else {
        formData.append(`nominees[${index}][aadhaar_doc]`, "");
      }

      // ✅ Add modified fields only for existing nominees
      if (nominee.nominee_id) {
        formData.append(
          `nominees[${index}][modified_by]`,
          String(loggedinuserid)
        );
        formData.append(
          `nominees[${index}][modified_on]`,
          new Date().toISOString()
        );
      }
    });

    // ✅ Check if there are ANY existing nominees
    const hasExistingNominees = values.nominees.some((n: any) => n.nominee_id);

    // Use update endpoint if in edit mode AND there are existing nominees
    if (mode === "edit" && hasExistingNominees) {
      updateDriverNominees.mutate(formData);
    } else {
      addDriverNominees.mutate(formData);
    }
  };

  const isReadOnly = readOnly || mode === "view";

  const addNominee = () => {
    append({
      relation: "",
      name: "",
      aadhaar_no: "",
      aadhaar_doc: "",
      mobile_no: "",
    });
  };

  useEffect(() => {
    console.log(form.formState.errors);
  }, [form.formState.errors]);

  return (
    <div className="w-full px-6 py-4">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Nominees
            </h3>
          </div>

          {fields.map((field, index) => (
            <div key={field.id} className="mb-8 relative">
              <div className="flex justify-between items-center mb-4 bg-gray-100 dark:bg-gray-800 px-4 py-3 rounded-md">
                <h4 className="text-md font-medium text-gray-800 dark:text-gray-200">
                  Nominee {index + 1}
                </h4>
                {fields.length > 1 && !isReadOnly && (
                  <Button
                    type="button"
                    onClick={() => remove(index)}
                    variant="destructive"
                    size="sm"
                    className="flex items-center gap-1"
                  >
                    <X className="w-4 h-4" />
                    Remove
                  </Button>
                )}
              </div>

              <div className="flex items-end gap-6">
                {/* Nominee Name */}
                <FormField
                  name={`nominees.${index}.name`}
                  control={form.control}
                  render={({ field }) => (
                    <FormItem className="flex flex-col">
                      <FormLabel>Nominee Name</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="Enter Nominee Name"
                          className="w-48"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Relation */}
                <FormField
                  name={`nominees.${index}.relation`}
                  control={form.control}
                  render={({ field }) => (
                    <FormItem className="flex flex-col">
                      <FormLabel>Relation</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        value={field.value}
                      >
                        <FormControl>
                          <SelectTrigger className="w-40">
                            <SelectValue placeholder="Select Relation" />
                          </SelectTrigger>
                        </FormControl>

                        <SelectContent>
                          <SelectItem value="none">Select Relation</SelectItem>
                          {RELATIONS.map((item) => (
                            <SelectItem key={item} value={item}>
                              {item}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Mobile */}
                <FormField
                  name={`nominees.${index}.mobile_no`}
                  control={form.control}
                  render={({ field }) => (
                    <FormItem className="flex flex-col">
                      <FormLabel>Mobile No.</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="Enter Mobile No."
                          className="w-40"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Aadhaar No */}
                <FormField
                  name={`nominees.${index}.aadhaar_no`}
                  control={form.control}
                  render={({ field }) => (
                    <FormItem className="flex flex-col">
                      <FormLabel>Aadhaar No.</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="Enter Aadhaar No."
                          className="w-40"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Aadhaar Upload (Clip Button) */}
                {/* Aadhaar Upload (Clip Button) */}
                <FormField
                  name={`nominees.${index}.aadhaar_doc`}
                  control={form.control}
                  render={({ field }) => {
                    const getDocumentUrl = () => {
                      if (field.value && typeof field.value === "string") {
                        if (field.value.startsWith("http")) {
                          return field.value;
                        }
                        const baseUrl = "http://localhost:4000";
                        const cleanPath = field.value.startsWith("/")
                          ? field.value
                          : `/${field.value}`;
                        return `${baseUrl}${cleanPath}`;
                      }
                      return null;
                    };

                    const documentUrl = getDocumentUrl();
                    const fileName =
                      field.value instanceof File
                        ? field.value.name
                        : field.value
                        ? field.value.split("/").pop()
                        : "";

                    return (
                      <FormItem className="flex flex-col">
                        <FormLabel>Aadhaar Doc</FormLabel>

                        <FormControl>
                          <div className="flex items-center gap-3">
                            <label className="cursor-pointer flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 border rounded-md w-fit">
                              <Paperclip className="w-4 h-4" />
                              <input
                                type="file"
                                className="hidden"
                                accept=".pdf,.doc,.docx"
                                onChange={(e) =>
                                  field.onChange(e.target.files?.[0] || null)
                                }
                              />
                            </label>

                            {field.value && (
                              <div className="flex items-center gap-2">
                                <FileText className="w-4 h-4 text-blue-600" />
                                <span className="text-sm text-gray-600">
                                  {fileName}
                                </span>
                                {documentUrl &&
                                  typeof field.value === "string" && (
                                    <a
                                      href={documentUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-xs text-blue-500 hover:underline"
                                    >
                                      View
                                    </a>
                                  )}
                              </div>
                            )}
                          </div>
                        </FormControl>

                        <FormMessage />
                      </FormItem>
                    );
                  }}
                />
              </div>

              {/* Show Add Nominee button only for the last nominee */}
              {index === fields.length - 1 && !isReadOnly && (
                <div className="mt-6">
                  <Button
                    type="button"
                    onClick={addNominee}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md flex items-center gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Add Nominee
                  </Button>
                </div>
              )}

              {index < fields.length - 1 && (
                <hr className="border-gray-300 dark:border-gray-700 mt-8" />
              )}
            </div>
          ))}

          {/* Single Save Button at the bottom */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            {!isReadOnly && (
              <Button
                type="submit"
                disabled={
                  addDriverNominees.isLoading || updateDriverNominees.isLoading
                }
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white"
              >
                {addDriverNominees.isLoading || updateDriverNominees.isLoading
                  ? "Saving..."
                  : mode === "edit"
                  ? "Update Nominees"
                  : "Save Nominees"}
              </Button>
            )}
          </div>
        </form>
      </Form>
    </div>
  );
};

export default DriverNomineeForm;
