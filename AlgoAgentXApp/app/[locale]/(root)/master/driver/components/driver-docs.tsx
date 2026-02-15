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
import { ChevronRight, FileText, Paperclip, Plus, X } from "lucide-react";
import {
  useDeleter,
  usePoster,
  usePosterWithFileUpload,
  useUpdater,
  useUpdaterWithFileUpload,
} from "@/hooks/use-query";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Cookies from "js-cookie";
import { useTranslation } from "@/hooks/use-translations";
import { DriverDocumentsSchema } from "@/schemas/driver-schema";
import { DriverDocuments } from "@/types/driver-type";
import { Country, State, City, IState, ICity } from "country-state-city";
import { useQueryClient } from "@tanstack/react-query";

type DriverDocFormProps = {
  driverId?: number | null;
  driverdocs?: DriverDocuments;
  initialData?: any;
  readOnly?: boolean;
  onSuccess?: () => void;
  onNext?: () => void;
};

type FormInputs = z.infer<typeof DriverDocumentsSchema>;

const DriverDocsForm = ({
  driverId,
  driverdocs,
  initialData = {},
  readOnly = false,
  onNext,
  onSuccess: onSuccessCallback,
}: DriverDocFormProps) => {
  const detectedMode = driverdocs?.document_id ? "edit" : "add";
  const { t, isRTL, locale } = useTranslation();
  const param = useParams();
  const router = useRouter();
  const isInitialized = useRef(false);
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));
  const [loggedincompanyid] = useState(Cookies.get("loggedincompanyid"));

  // ✅ MOVE THESE BEFORE form initialization
  const searchParams = useSearchParams();
  const routeDriverId =
    Number(searchParams.get("driver_id")) ||
    Number(localStorage.getItem("driver_id"));

  const form = useForm<FormInputs>({
    resolver: zodResolver(DriverDocumentsSchema),
    defaultValues: {
      ...initialData,
      license_no: "",
      issue_authourity: "",
      license_issue_address: "",
      license_iisue_district: "",
      license_iisue_state: "",
      license_iisue_date: "",
      license_expiry_date: "",
      license_denied: "",
      license_expense: "",

      // ✅ ADD REQUIRED FIELDS HERE
      driver_id: routeDriverId,
      status: "Active",
      created_by: Number(loggedinuserid),
      created_on: new Date().toISOString(),

      endorsement_no: "",
      endorsement_issue_authority: "",
      endorsement_address: "",
      endorsement_country: "",
      endorsement_state: "",
      endorsement_city: "",
      endorsement_district: "",
      endorsement_issue_date: "",
      endorsement_expire_date: "",

      harzardous_no: "",
      hrds_issue_authority: "",
      hrds_address: "",
      hrds_issue_date: "",
      hrds_expire_date: "",

      hrds_endorsement_no: "",
      hrds_endorsement_issue_authority: "",
      hrds_endorsement_address: "",
      hrds_endorsement_country: "",
      hrds_endorsement_state: "",
      hrds_endorsement_city: "",
      hrds_endorsement_district: "",
      hrds_endorsement_issue_date: "",
      hrds_endorsement_expire_date: "",
    },
  });

  useEffect(() => {
    if (initialData) {
      form.reset({
        ...form.getValues(),
        ...initialData,
      });
    }
  }, [initialData]);

  const [endorsementStates, setEndorsementStates] = useState<IState[]>([]);
  const [endorsementCities, setEndorsementCities] = useState<ICity[]>([]);

  const [hrdsStates, setHrdsStates] = useState<IState[]>([]);
  const [hrdsCities, setHrdsCities] = useState<ICity[]>([]);

  const onEndorsementCountryChange = (code: string) => {
    const co = Country.getCountryByCode(code)?.name;

    form.setValue("endorsement_country", co || "");
    form.setValue("endorsement_state", "");
    form.setValue("endorsement_city", "");

    const newStates = State.getStatesOfCountry(code);
    setEndorsementStates(newStates);
    setEndorsementCities([]);
  };

  const onEndorsementStateChange = (code: string) => {
    const countryCode = Country.getAllCountries().find(
      (c) => c.name === form.getValues("endorsement_country")
    )?.isoCode;

    const st = State.getStateByCodeAndCountry(code, countryCode!)?.name;

    form.setValue("endorsement_state", st || "");
    form.setValue("endorsement_city", "");

    const newCities = City.getCitiesOfState(countryCode!, code);
    setEndorsementCities(newCities);
  };

  const onEndorsementCityChange = (cityName: string) => {
    form.setValue("endorsement_city", cityName);
    // district is text input so we DO NOT auto-fill anything
    form.setValue("endorsement_district", "");
  };

  const onHazardousCountryChange = (code: string) => {
    const co = Country.getCountryByCode(code)?.name;

    form.setValue("hrds_endorsement_country", co || "");
    form.setValue("hrds_endorsement_state", "");
    form.setValue("hrds_endorsement_city", "");

    const newStates = State.getStatesOfCountry(code);
    setHrdsStates(newStates); // ✅ Use hrdsStates
    setHrdsCities([]); // ✅ Use hrdsCities
  };

  const onHazardousStateChange = (code: string) => {
    const countryCode = Country.getAllCountries().find(
      (c) => c.name === form.getValues("hrds_endorsement_country")
    )?.isoCode;

    const st = State.getStateByCodeAndCountry(code, countryCode!)?.name;

    form.setValue("hrds_endorsement_state", st || "");
    form.setValue("hrds_endorsement_city", "");

    const newCities = City.getCitiesOfState(countryCode!, code);
    setHrdsCities(newCities); // ✅ Use hrdsCities
  };

  const onHazardousCityChange = (cityName: string) => {
    form.setValue("hrds_endorsement_city", cityName);
    form.setValue("hrds_endorsement_district", "");
  };

  const queryClient = useQueryClient();

  const onSuccess = (response: any) => {
    const updatedDoc = response[0];

    // Correct toast
    Toast.fire({
      icon: "success",
      title:
        detectedMode === "edit"
          ? "Driver Documents updated successfully"
          : "Driver Documents added successfully",
    });

    // Correct query invalidation
    queryClient.invalidateQueries({
      queryKey: ["driverfullbyid"],
    });

    // Reset UI with updated values
    if (detectedMode === "edit") {
      form.reset({
        ...form.getValues(),
        ...updatedDoc,
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

  const addDriverDocs = usePosterWithFileUpload(
    "/driver/add-driver-documents",
    "AddDriverDocs",
    onSuccess,
    onError
  );

  const updateDriverDocs = useUpdaterWithFileUpload(
    `/driver/update-driver-documents/${driverdocs?.document_id}`,
    "driverbyid",
    onSuccess,
    onError
  );

  const onSubmit = (values: any) => {
    const formData = new FormData();
    // const driverId = Number(localStorage.getItem("driver_id"));
    const routeDriverId =
      detectedMode === "edit"
        ? Number(param["id"])
        : Number(searchParams.get("driver_id")) ||
          Number(localStorage.getItem("driver_id"));

    const toISODateTime = (dateStr: string) => {
      if (!dateStr || dateStr.trim() === "") return null;
      return new Date(dateStr).toISOString();
    };

    const cleanValues = {
      ...values,
      license_iisue_date: toISODateTime(values.license_iisue_date),
      license_expiry_date: toISODateTime(values.license_expiry_date),
      endorsement_issue_date: toISODateTime(values.endorsement_issue_date),
      endorsement_expire_date: toISODateTime(values.endorsement_expire_date),
      hrds_issue_date: toISODateTime(values.hrds_issue_date),
      hrds_expire_date: toISODateTime(values.hrds_expire_date),
      hrds_endorsement_issue_date: toISODateTime(
        values.hrds_endorsement_issue_date
      ),
      hrds_endorsement_expire_date: toISODateTime(
        values.hrds_endorsement_expire_date
      ),
    };

    const document = {
      ...cleanValues,
      driver_id: routeDriverId,
      status: "Active",
    };

    // ✅ Add document_id for UPDATE
    if (detectedMode === "edit") {
      document.document_id = driverdocs?.document_id; // ONLY this!
      document.modified_by = Number(loggedinuserid);
      document.modified_on = new Date().toISOString();
    } else {
      // Only set created_by/created_on for NEW documents
      document.created_by = Number(loggedinuserid);
      document.created_on = new Date().toISOString();
      document.status = "Active";
    }

    console.log("🔍 driverdocs prop:", driverdocs);
    console.log("🔍 param['id']:", param["id"]);

    const dto = {
      driver_id: routeDriverId,
      documents: [document],
    };

    formData.append("data", JSON.stringify(dto));

    if (values.license_doc instanceof File) {
      formData.append("files", values.license_doc);
    }

    // ✅ Call correct mutation based on mode
    if (detectedMode === "edit") {
      updateDriverDocs.mutate(formData); // ✅ Should call UPDATE
    } else {
      addDriverDocs.mutate(formData);
    }
  };

  const isReadOnly = readOnly;

  useEffect(() => {
    console.log(form.formState.errors);
  }, [form.formState.errors]);

  return (
    <div className="w-full px-6 py-4">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <div>
            {/* License Details Section */}
            <div className="mb-8">
              <h2 className="text-base font-medium text-gray-900 dark:text-gray-100 mb-6">
                License Details
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* License No./Issue Authority */}
                <FormField
                  control={form.control}
                  name="license_no"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        License No.
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter License No./Authority"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="issue_authourity"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        Issue Authority
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Issue Authority"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* License Issue Address */}
                <FormField
                  control={form.control}
                  name="license_issue_address"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        License Issue Address
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Issue Address"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* License Issue District */}
                <FormField
                  control={form.control}
                  name="license_iisue_district"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        License Issue District
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Issue District"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* License Issue State */}
                <FormField
                  control={form.control}
                  name="license_iisue_state"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        License Issue State
                      </FormLabel>

                      <Select
                        value={field.value || ""}
                        onValueChange={(value) => field.onChange(value)}
                        disabled={isReadOnly}
                      >
                        <FormControl>
                          <SelectTrigger className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm">
                            <SelectValue placeholder="Select Issue State" />
                          </SelectTrigger>
                        </FormControl>

                        <SelectContent>
                          {State.getStatesOfCountry("IN").map((s) => (
                            <SelectItem key={s.isoCode} value={s.name}>
                              {s.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* License Issue Date */}
                <FormField
                  control={form.control}
                  name="license_iisue_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        License Issue Date
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="date"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-36 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* License Expiry Date */}
                <FormField
                  control={form.control}
                  name="license_expiry_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        License Expiry Date
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="date"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-36 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* License Doc */}
                {/* License Doc */}
                <FormField
                  name="license_doc"
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
                    const isFile =
                      field.value &&
                      typeof field.value === "object" &&
                      "name" in (field.value as any);
                    const fileName = isFile
                      ? (field.value as unknown as File).name
                      : field.value
                      ? (field.value as string).split("/").pop()
                      : "";

                    return (
                      <FormItem className="flex flex-col">
                        <FormLabel>License Document (PDF / DOC)</FormLabel>

                        <FormControl>
                          <div className="flex items-center gap-3">
                            {/* Upload Button */}
                            <label className="cursor-pointer flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 border rounded-md w-fit">
                              <Paperclip className="w-4 h-4" />
                              <input
                                type="file"
                                className="hidden"
                                accept=".pdf,.doc,.docx,image/*"
                                onChange={(e) => {
                                  const file = e.target.files?.[0] || null;
                                  field.onChange(file);
                                }}
                              />
                            </label>

                            {/* File Display */}
                            {fileName && (
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

                {/* License Denied */}
                <FormField
                  control={form.control}
                  name="license_denied"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        License Denied
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter License Denied"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* License Expense */}
                <FormField
                  control={form.control}
                  name="license_expense"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        License Expense
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter License Expense"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Driver ID */}
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-base font-medium text-gray-900 dark:text-gray-100 mb-6">
                Endorsement Details
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Endorsement No. */}
                <FormField
                  control={form.control}
                  name="endorsement_no"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        Endorsement No.
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Endorsement No."
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Endorsement Issue Authority */}
                <FormField
                  control={form.control}
                  name="endorsement_issue_authority"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        Endorsement Issue Authority
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Issue Authority"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Endorsement Address */}
                <FormField
                  control={form.control}
                  name="endorsement_address"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        Endorsement Address
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Address"
                          {...field}
                          readOnly={isReadOnly}
                          className="h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Endorsement Country */}
                <FormField
                  control={form.control}
                  name="endorsement_country"
                  render={({ field }) => {
                    // Find the country code from the stored country name
                    const selectedCountryCode =
                      Country.getAllCountries().find(
                        (c) => c.name === field.value
                      )?.isoCode || "";

                    return (
                      <FormItem>
                        <FormLabel>Endorsement Country</FormLabel>
                        <Select
                          value={selectedCountryCode}
                          onValueChange={(value) => {
                            onEndorsementCountryChange(value);
                          }}
                          disabled={isReadOnly}
                        >
                          <SelectTrigger className="w-72">
                            <SelectValue placeholder="Select Country" />
                          </SelectTrigger>
                          <SelectContent>
                            {Country.getAllCountries().map((c) => (
                              <SelectItem key={c.isoCode} value={c.isoCode}>
                                {c.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    );
                  }}
                />

                {/* Endorsement State */}
                <FormField
                  control={form.control}
                  name="endorsement_state"
                  render={({ field }) => {
                    // Find the state code from the stored state name
                    const selectedStateCode =
                      endorsementStates.find((s) => s.name === field.value)
                        ?.isoCode || "";

                    return (
                      <FormItem>
                        <FormLabel>Endorsement State</FormLabel>
                        <Select
                          value={selectedStateCode}
                          onValueChange={(value) => {
                            onEndorsementStateChange(value);
                          }}
                          disabled={isReadOnly}
                        >
                          <SelectTrigger className="w-72">
                            <SelectValue placeholder="Select State" />
                          </SelectTrigger>
                          <SelectContent>
                            {endorsementStates.map((s) => (
                              <SelectItem key={s.isoCode} value={s.isoCode}>
                                {s.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    );
                  }}
                />

                {/* Endorsement City */}
                <FormField
                  control={form.control}
                  name="endorsement_city"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Endorsement City</FormLabel>
                      <Select
                        value={field.value || ""}
                        onValueChange={(value) => {
                          onEndorsementCityChange(value);
                        }}
                        disabled={isReadOnly}
                      >
                        <SelectTrigger className="w-72">
                          <SelectValue placeholder="Select City" />
                        </SelectTrigger>
                        <SelectContent>
                          {endorsementCities.map((c) => (
                            <SelectItem key={c.name} value={c.name}>
                              {c.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Endorsement District */}
                <FormField
                  control={form.control}
                  name="endorsement_district"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Endorsement District</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter District"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Endorsement Issue Date */}
                <FormField
                  control={form.control}
                  name="endorsement_issue_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        Endorsement Issue Date
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="date"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-36 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Endorsement Expire Date */}
                <FormField
                  control={form.control}
                  name="endorsement_expire_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        Endorsement Expire Date
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="date"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-36 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Hazardous Training Card Section */}
            <div className="mb-8">
              <h2 className="text-base font-medium text-gray-900 dark:text-gray-100 mb-6">
                Hazardous Training Card
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Hazardous No. */}
                <FormField
                  control={form.control}
                  name="harzardous_no"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        Hazardous No.
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Hazardous No."
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* HRDS Issue Authority */}
                <FormField
                  control={form.control}
                  name="hrds_issue_authority"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        HRDS Issue Authority
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Issue Authority"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* HRDS Address */}
                <FormField
                  control={form.control}
                  name="hrds_address"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        HRDS Address
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Address"
                          {...field}
                          readOnly={isReadOnly}
                          className="h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* HRDS Issue Date */}
                <FormField
                  control={form.control}
                  name="hrds_issue_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        HRDS Issue Date
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="date"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-36 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* HRDS Expire Date */}
                <FormField
                  control={form.control}
                  name="hrds_expire_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        HRDS Expire Date
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="date"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-36 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Hazardous Endorsement Section */}
            {/* Hazardous Endorsement Section */}
            <div className="mb-8">
              <h2 className="text-base font-medium text-gray-900 dark:text-gray-100 mb-6">
                Hazardous Endorsement Details
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* HRDS Endorsement No. */}
                <FormField
                  control={form.control}
                  name="hrds_endorsement_no"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        HRDS Endorsement No.
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Endorsement No."
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* HRDS Endorsement Issue Authority */}
                <FormField
                  control={form.control}
                  name="hrds_endorsement_issue_authority"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        HRDS Endorsement Issue Authority
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Issue Authority"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* HRDS Endorsement Address */}
                <FormField
                  control={form.control}
                  name="hrds_endorsement_address"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        HRDS Endorsement Address
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Address"
                          {...field}
                          readOnly={isReadOnly}
                          className="h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* HRDS Endorsement Country */}
                <FormField
                  control={form.control}
                  name="hrds_endorsement_country"
                  render={({ field }) => {
                    // Find the country code from the stored country name
                    const selectedCountryCode =
                      Country.getAllCountries().find(
                        (c) => c.name === field.value
                      )?.isoCode || "";

                    return (
                      <FormItem>
                        <FormLabel>HRDS Endorsement Country</FormLabel>
                        <Select
                          value={selectedCountryCode}
                          onValueChange={(value) => {
                            onHazardousCountryChange(value);
                          }}
                          disabled={isReadOnly}
                        >
                          <SelectTrigger className="w-72">
                            <SelectValue placeholder="Select Country" />
                          </SelectTrigger>
                          <SelectContent>
                            {Country.getAllCountries().map((c) => (
                              <SelectItem key={c.isoCode} value={c.isoCode}>
                                {c.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    );
                  }}
                />

                {/* HRDS Endorsement State */}
                <FormField
                  control={form.control}
                  name="hrds_endorsement_state"
                  render={({ field }) => {
                    // Find the state code from the stored state name
                    const selectedStateCode =
                      hrdsStates.find((s) => s.name === field.value)?.isoCode ||
                      "";

                    return (
                      <FormItem>
                        <FormLabel>HRDS Endorsement State</FormLabel>
                        <Select
                          value={selectedStateCode}
                          onValueChange={(value) => {
                            onHazardousStateChange(value);
                          }}
                          disabled={isReadOnly}
                        >
                          <SelectTrigger className="w-72">
                            <SelectValue placeholder="Select State" />
                          </SelectTrigger>
                          <SelectContent>
                            {hrdsStates.map((s) => (
                              <SelectItem key={s.isoCode} value={s.isoCode}>
                                {s.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    );
                  }}
                />

                {/* HRDS Endorsement City */}
                <FormField
                  control={form.control}
                  name="hrds_endorsement_city"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>HRDS Endorsement City</FormLabel>
                      <Select
                        value={field.value || ""}
                        onValueChange={(value) => {
                          onHazardousCityChange(value);
                        }}
                        disabled={isReadOnly}
                      >
                        <SelectTrigger className="w-72">
                          <SelectValue placeholder="Select City" />
                        </SelectTrigger>
                        <SelectContent>
                          {hrdsCities.map((c) => (
                            <SelectItem key={c.name} value={c.name}>
                              {c.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* HRDS Endorsement District */}
                <FormField
                  control={form.control}
                  name="hrds_endorsement_district"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>HRDS Endorsement District</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter District"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-72 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* HRDS Endorsement Issue Date */}
                <FormField
                  control={form.control}
                  name="hrds_endorsement_issue_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        HRDS Endorsement Issue Date
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="date"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-36 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* HRDS Endorsement Expire Date */}
                <FormField
                  control={form.control}
                  name="hrds_endorsement_expire_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-normal text-gray-700 dark:text-gray-300">
                        HRDS Endorsement Expire Date
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="date"
                          {...field}
                          readOnly={isReadOnly}
                          className="w-36 h-10 rounded border border-gray-300 dark:border-gray-700 px-3 text-sm"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Action Buttons */}
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            {!isReadOnly && (
              <Button
                type="submit"
                disabled={addDriverDocs.isLoading || updateDriverDocs.isLoading}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white"
              >
                {addDriverDocs.isLoading || updateDriverDocs.isLoading
                  ? "Saving..."
                  : detectedMode === "edit"
                  ? "Update Document"
                  : "Save Document"}
              </Button>
            )}
          </div>
        </form>
      </Form>
    </div>
  );
};

export default DriverDocsForm;
