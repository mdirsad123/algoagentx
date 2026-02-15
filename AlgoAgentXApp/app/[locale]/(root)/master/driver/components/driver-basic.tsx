"use client";

import React, { useEffect, useState } from "react";
import {
  Upload,
  ChevronDown,
  ChevronRight,
  FileText,
  Paperclip,
} from "lucide-react";
import * as z from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { driverBasicSchema } from "@/schemas/driver-schema";
import { DriverBasic } from "@/types/driver-type";

import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";
import {
  usePoster,
  useFetcher,
  useDeleter,
  useUpdater,
  usePosterWithFileUpload,
  useUpdaterWithFileUpload,
} from "@/hooks/use-query";
import { useParams, useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectItem,
  SelectContent,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import Cookies from "js-cookie";
import Toast from "@/components/shared/toast";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Country, State, City, IState, ICity } from "country-state-city";

type DriverBasicFormProps = {
  driverbasic?: DriverBasic;
  id?: number | string;
  initialData?: any;
  mode?: "add" | "edit" | "view";
  onNext?: () => void;
  readOnly?: boolean;
};

type FormInputs = z.infer<typeof driverBasicSchema>;

const DriverBasicForm = ({
  id,
  driverbasic,
  initialData = {},
  mode = "add",
  onNext,
  readOnly = false,
}: DriverBasicFormProps) => {
  const param = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [loggedincompanyid] = useState(Cookies.get("loggedincompanyid"));
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));

  const form = useForm<FormInputs>({
    resolver: zodResolver(driverBasicSchema),
    defaultValues: {},
  });

  // In driver-basic.tsx, REPLACE the useEffect at line ~50:

  const normalizeValue = (value: string | undefined, options: string[]) => {
    if (!value) return "";
    return (
      options.find((opt) => opt.toLowerCase() === value.toLowerCase().trim()) ||
      ""
    );
  };

  useEffect(() => {
    if (initialData && Object.keys(initialData).length > 0) {
      const formattedData = { ...initialData };

      // Convert ISO date strings to yyyy-MM-dd format
      ["date_of_birth", "joining_date", "opening_balance_date"].forEach(
        (field) => {
          if (formattedData[field]) {
            const date = new Date(formattedData[field]);
            if (!isNaN(date.getTime())) {
              formattedData[field] = date.toISOString().split("T")[0];
            }
          }
        }
      );

      // Convert language_known string to array
      if (
        formattedData.language_known &&
        typeof formattedData.language_known === "string"
      ) {
        formattedData.language_known = formattedData.language_known
          .split(",")
          .map((lang: string) => lang.trim());
      }

      // ✅ ADD: Load country/state/city dropdowns
      if (formattedData.country) {
        const countryCode = Country.getAllCountries().find(
          (c) => c.name === formattedData.country
        )?.isoCode;

        if (countryCode) {
          const stateList = State.getStatesOfCountry(countryCode);
          setPermStates(stateList);

          if (formattedData.state) {
            const stateCode = stateList.find(
              (s) => s.name === formattedData.state
            )?.isoCode;

            if (stateCode) {
              const cityList = City.getCitiesOfState(countryCode, stateCode);
              setPermCities(cityList);
            }
          }
        }
      }

      // ✅ LOAD PRESENT COUNTRY / STATE / CITY (EDIT MODE)
      if (formattedData.present_country) {
        const presCountryCode = Country.getAllCountries().find(
          (c) => c.name === formattedData.present_country
        )?.isoCode;

        if (presCountryCode) {
          const presStateList = State.getStatesOfCountry(presCountryCode);
          setPresStates(presStateList);

          if (formattedData.present_state) {
            const presStateCode = presStateList.find(
              (s) => s.name === formattedData.present_state
            )?.isoCode;

            if (presStateCode) {
              const presCityList = City.getCitiesOfState(
                presCountryCode,
                presStateCode
              );
              setPresCities(presCityList);
            }
          }
        }
      }

      // -----------------------------
      // 🔧 FIX: Normalize static dropdown values (EDIT MODE)
      // -----------------------------
      formattedData.hair_colour = normalizeValue(
        formattedData.hair_colour,
        hairColors
      );

      formattedData.martial_status = normalizeValue(
        formattedData.martial_status,
        ["Single", "Married", "Divorced", "Widowed", "Separated"]
      );

      formattedData.blood_group = normalizeValue(
        formattedData.blood_group,
        bloodGroups
      );

      formattedData.religion = normalizeValue(
        formattedData.religion,
        religions
      );

      form.reset(formattedData);
    }
  }, [initialData, form]);

  const [permStates, setPermStates] = useState<IState[]>([]);
  const [permCities, setPermCities] = useState<ICity[]>([]);

  const [presStates, setPresStates] = useState<IState[]>([]);
  const [presCities, setPresCities] = useState<ICity[]>([]);

  const onCountryChange = (code: string) => {
    const co = Country.getCountryByCode(code)?.name;

    form.setValue("present_country", co || "");
    form.setValue("present_state", "");
    form.setValue("present_city", "");

    const newStates = State.getStatesOfCountry(code);
    setPresStates(newStates);
    setPresCities([]);
  };

  const onStateChange = (code: string) => {
    const countryCode = Country.getAllCountries().find(
      (c) => c.name === form.getValues("present_country")
    )?.isoCode;

    const st = State.getStateByCodeAndCountry(code, countryCode!)?.name;

    form.setValue("present_state", st || "");
    form.setValue("present_city", "");

    const newCities = City.getCitiesOfState(countryCode!, code);
    setPresCities(newCities);
  };

  const onCityChange = (cityName: string) => {
    form.setValue("present_city", cityName);
    // district is text input so we DO NOT auto-fill anything
    form.setValue("present_district", "");
  };

  const onSuccess = (response: any) => {
    Toast.fire({
      icon: "success",
      title:
        mode === "edit"
          ? "Driver Basic updated successfully"
          : "Driver Basic added successfully",
    });

    // Save driver_id for nominee tab
    const driverId = response?.driver_id || driverbasic?.driver_id || id;
    if (driverId) {
      localStorage.setItem("driver_id", driverId.toString());
    }

    // ✅ ADD THIS - Invalidate and refetch the driver data
    if (mode === "edit") {
      queryClient.invalidateQueries({ queryKey: ["driverfullbyid"] });
    }

    // Move to next tab
    if (onNext) onNext();
  };

  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e?.response?.data?.message || "Submission Failed",
    });
  };

  const addDriverBasics = usePosterWithFileUpload(
    "/driver/add-driver-personal",
    "AddDriverBasic",
    onSuccess,
    onError
  );

  // Get the correct driver ID, filtering out "null" strings
  const driverId =
    driverbasic?.driver_id ||
    id ||
    (param.id && param.id !== "null" ? param.id : null);

  console.log("🔍 Driver ID for update:", driverId);

  const updateDriverBsics = useUpdaterWithFileUpload(
    driverId
      ? `/driver/update-driver-personal/${driverId}`
      : `/driver/update-driver-personal/0`,
    "driverbasicupdatebyid",
    onSuccess,
    onError
  );

  const onSubmit = (values: any) => {
    console.log("🔥 SUBMIT FIRED");

    const currentDate = new Date();
    const formData = new FormData();
    let data: any = { ...values };

    // -----------------------------
    // 1️⃣ ARRAY → CSV CONVERSION
    // -----------------------------
    if (Array.isArray(values.language_known)) {
      data.language_known = values.language_known.join(",");
    }

    // -----------------------------
    // 2️⃣ ADD / UPDATE Metadata
    // -----------------------------
    if (mode === "edit") {
      data.modified_on = currentDate;
      data.modified_by = Number(loggedinuserid);
      data.companyid = Number(loggedincompanyid);
    } else {
      data.created_on = currentDate;
      data.created_by = Number(loggedinuserid);
      data.companyid = Number(loggedincompanyid);
      data.status = "Active";
    }

    // -----------------------------
    // 3️⃣ SAFE APPEND: Flat Fields Only
    // -----------------------------
    Object.entries(data).forEach(([key, value]) => {
      if (value === undefined || value === null) return;

      // Files handled separately
      if (value instanceof File) return;

      // Convert objects {} → string safely
      if (typeof value === "object") {
        value = JSON.stringify(value);
      }

      // Convert numbers & booleans to string
      formData.append(key, String(value));
    });

    // -----------------------------
    // 4️⃣ APPEND FILES SEPARATELY
    // -----------------------------
    if (values.driver_img instanceof File) {
      formData.append("driver_img", values.driver_img);
    }

    if (values.adhar_doc instanceof File) {
      formData.append("adhar_doc", values.adhar_doc);
    }

    // -----------------------------
    // 5️⃣ ADD "data" FIELD ONLY FOR UPDATE
    // -----------------------------
    if (mode === "edit") {
      formData.append("data", JSON.stringify(data));
    }

    // -----------------------------
    // 6️⃣ DEBUG
    // -----------------------------
    console.log("📦 FINAL FORMDATA SENT:");
    formData.forEach((value, key) => {
      console.log(key, value);
    });

    // -----------------------------
    // 7️⃣ CALL API
    // -----------------------------
    if (mode === "edit") {
      updateDriverBsics.mutate(formData);
    } else {
      addDriverBasics.mutate(formData);
    }
  };

  const religions = [
    "Hinduism",
    "Islam",
    "Christianity",
    "Sikhism",
    "Buddhism",
    "Jainism",
    "Zoroastrianism",
    "Judaism",
    "Bahá'í Faith",
    "Other",
  ];

  const bloodGroups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

  const hairColors = [
    "Black",
    "Brown",
    "Blonde",
    "Red",
    "Grey",
    "White",
    "Other",
  ];

  const isReadOnly = readOnly || mode === "view";

  const today = new Date();
  const minAgeDate = new Date(
    today.getFullYear() - 18,
    today.getMonth(),
    today.getDate()
  );
  const maxDobAllowed = minAgeDate.toISOString().split("T")[0];

  const [sameAsPermanent, setSameAsPermanent] = useState(false);

  const handleSameAsPermanent = (checked: boolean) => {
    setSameAsPermanent(checked);

    if (!checked) return;

    // Copy simple fields
    form.setValue("present_address", form.getValues("param_address"));
    form.setValue("present_district", form.getValues("district"));
    form.setValue("present_taluka", form.getValues("taluka"));
    form.setValue("present_mobile_no", form.getValues("mobile_no"));

    // Copy country / state / city (by NAME – matches your form design)
    const countryName = form.getValues("country");
    const stateName = form.getValues("state");
    const cityName = form.getValues("city");

    form.setValue("present_country", countryName || "");
    form.setValue("present_state", stateName || "");
    form.setValue("present_city", cityName || "");

    // Load state & city dropdowns correctly
    const countryCode = Country.getAllCountries().find(
      (c) => c.name === countryName
    )?.isoCode;

    if (countryCode) {
      const states = State.getStatesOfCountry(countryCode);
      setPresStates(states);

      const stateCode = states.find((s) => s.name === stateName)?.isoCode;
      if (stateCode) {
        const cities = City.getCitiesOfState(countryCode, stateCode);
        setPresCities(cities);
      }
    }
  };

  useEffect(() => {
    console.log(form.formState.errors);
  }, [form.formState.errors]);

  return (
    <div className="w-full px-6 py-4">
      <h2 className="text-2xl font-semibold text-gray-900 mb-6">
        Driver Master
      </h2>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* ROW 1 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="driver_code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Driver Code</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter driver code"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="driver_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Driver Name</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter driver name "
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="gender"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Gender (M/F)</FormLabel>

                  <div className="flex items-center gap-6 mt-2">
                    {/* Male */}
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="gender"
                        value="M"
                        checked={field.value === "M"}
                        onChange={() => field.onChange("M")}
                        className="h-4 w-4 rounded-full"
                      />
                      <span>M</span>
                    </label>

                    {/* Female */}
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="gender"
                        value="F"
                        checked={field.value === "F"}
                        onChange={() => field.onChange("F")}
                        className="h-4 w-4 rounded-full"
                      />
                      <span>F</span>
                    </label>
                  </div>

                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* ROW: Gender / Age / Previous Employed */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="date_of_birth"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Date of Birth</FormLabel>
                  <FormControl>
                    <Input
                      type="date"
                      className="w-36"
                      value={field.value || ""}
                      max={maxDobAllowed} // ✅ 18+ restriction
                      onChange={(e) => {
                        const selectedDate = e.target.value;
                        field.onChange(selectedDate);

                        const dob = new Date(selectedDate);
                        const today = new Date();
                        let age = today.getFullYear() - dob.getFullYear();
                        const m = today.getMonth() - dob.getMonth();
                        if (
                          m < 0 ||
                          (m === 0 && today.getDate() < dob.getDate())
                        ) {
                          age--;
                        }

                        // ✅ only allow valid 18+ age
                        form.setValue("age", age >= 18 ? age : 0);
                      }}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="age"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Age</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={0}
                      className="w-28"
                      value={field.value || ""}
                      onChange={(e) => {
                        field.onChange(e.target.value);

                        const age = Number(e.target.value);
                        if (!age) return;

                        const today = new Date();
                        const dob = new Date(
                          today.getFullYear() - age,
                          today.getMonth(),
                          today.getDate()
                        );

                        form.setValue(
                          "date_of_birth",
                          dob.toISOString().split("T")[0]
                        );
                      }}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="prev_employed"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Previous Employed</FormLabel>
                  <Input
                    {...field}
                    placeholder="Enter previous employment details"
                    className="w-72"
                  />
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Issue Date / Issue Place / Driver Image */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="joining_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Joining Date</FormLabel>
                  <FormControl>
                    <Input {...field} type="date" className="w-36" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="location"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Joining Place</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter joining place"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="driver_img"
              render={({ field }) => {
                // Construct the full URL for existing images
                const getImageUrl = () => {
                  if (field.value instanceof File) {
                    return URL.createObjectURL(field.value);
                  }
                  if (field.value && typeof field.value === "string") {
                    // If it's already a full URL, use it
                    if (field.value.startsWith("http")) {
                      return field.value;
                    }
                    // Handle paths like "/uploads/1765539519053-70519616.png"
                    const baseUrl =
                      process.env.NEXT_PUBLIC_API_URL ||
                      "http://localhost:4000";
                    // Remove trailing slash from baseUrl if exists
                    const cleanBaseUrl = baseUrl.endsWith("/")
                      ? baseUrl.slice(0, -1)
                      : baseUrl;
                    // Ensure path starts with /
                    const cleanPath = field.value.startsWith("/")
                      ? field.value
                      : `/${field.value}`;
                    return `${cleanBaseUrl}${cleanPath}`;
                  }
                  return null;
                };

                const imageUrl = getImageUrl();

                return (
                  <FormItem>
                    <FormLabel>Driver Image (Photo)</FormLabel>

                    <div
                      className="w-full h-48 border-2 border-dashed border-gray-300 rounded flex flex-col items-center justify-center cursor-pointer hover:border-gray-400 transition-colors"
                      onClick={() =>
                        !isReadOnly &&
                        document.getElementById("driverImgInput")?.click()
                      }
                    >
                      {imageUrl ? (
                        <div className="relative w-full h-full group">
                          <img
                            src={imageUrl}
                            alt="Driver"
                            className="object-cover w-full h-full rounded"
                            onError={(e) => {
                              console.error("Image failed to load:", imageUrl);
                              e.currentTarget.src =
                                'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><text y="50" font-size="14">Image not found</text></svg>';
                            }}
                          />
                          {!isReadOnly && (
                            <div className="absolute inset-0 bg-black bg-opacity-50 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                              <p className="text-white text-sm">
                                Click to change
                              </p>
                            </div>
                          )}
                        </div>
                      ) : (
                        <>
                          <Upload className="w-8 h-8 text-gray-400" />
                          <p className="text-sm text-gray-500">Upload Image</p>
                        </>
                      )}
                    </div>

                    {/* REAL FILE INPUT */}
                    <input
                      id="driverImgInput"
                      type="file"
                      accept="image/*"
                      className="hidden"
                      disabled={isReadOnly}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        console.log("Driver image selected:", file);
                        field.onChange(file);
                      }}
                    />

                    <FormMessage />
                  </FormItem>
                );
              }}
            />
          </div>

          {/* PIN  */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="pan_no"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>PAN No</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter PAN No."
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="adhar_no"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Aadhar No</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Aadhar No."
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="adhar_doc"
              render={({ field }) => {
                // Construct the full URL for existing documents
                const getDocumentUrl = () => {
                  if (field.value && typeof field.value === "string") {
                    if (field.value.startsWith("http")) {
                      return field.value;
                    }
                    // Handle paths like "/uploads/1765539519057-621105408.pdf"
                    const baseUrl =
                      process.env.NEXT_PUBLIC_API_URL ||
                      "http://localhost:4000";
                    const cleanBaseUrl = baseUrl.endsWith("/")
                      ? baseUrl.slice(0, -1)
                      : baseUrl;
                    const cleanPath = field.value.startsWith("/")
                      ? field.value
                      : `/${field.value}`;
                    return `${cleanBaseUrl}${cleanPath}`;
                  }
                  return null;
                };

                const documentUrl = getDocumentUrl();
                const fileName =
                  field.value instanceof File
                    ? field.value.name
                    : field.value
                    ? field.value.split("/").pop()
                    : null;

                return (
                  <FormItem>
                    <FormLabel>Aadhar Document (PDF / DOC)</FormLabel>

                    <div className="flex items-center gap-3">
                      {/* Paperclip Upload Button */}
                      <button
                        type="button"
                        onClick={() =>
                          !isReadOnly &&
                          document.getElementById("adharDocInput")?.click()
                        }
                        disabled={isReadOnly}
                        className="flex items-center justify-center w-10 h-10 rounded border bg-gray-100 hover:bg-gray-200 disabled:opacity-50"
                      >
                        <Paperclip className="w-5 h-5 text-gray-700" />
                      </button>

                      {/* File Preview / Existing Doc */}
                      {field.value && (
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-blue-600" />
                          <span className="text-sm text-gray-600 max-w-[200px] truncate">
                            {fileName}
                          </span>

                          {documentUrl && typeof field.value === "string" && (
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

                    <input
                      id="adharDocInput"
                      type="file"
                      accept=".pdf,.doc,.docx,image/*"
                      className="hidden"
                      disabled={isReadOnly}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        console.log("Aadhar Doc selected:", file);
                        field.onChange(file);
                      }}
                    />

                    <FormMessage />
                  </FormItem>
                );
              }}
            />
          </div>

          {/* Permanent Address */}
          <FormField
            control={form.control}
            name="param_address"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Permanent Address</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* City / Taluka / District */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="country"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Country</FormLabel>
                  <Select
                    value={field.value || ""}
                    onValueChange={(countryName) => {
                      // Store the country NAME in form
                      field.onChange(countryName);

                      // Find country code for fetching states
                      const countryCode = Country.getAllCountries().find(
                        (c) => c.name === countryName
                      )?.isoCode;

                      if (countryCode) {
                        const newStates = State.getStatesOfCountry(countryCode);
                        setPermStates(newStates);
                        setPermCities([]);
                        form.setValue("state", "");
                        form.setValue("city", "");
                      }
                    }}
                    disabled={isReadOnly}
                  >
                    <SelectTrigger className="w-72">
                      <SelectValue placeholder="Select Country" />
                    </SelectTrigger>
                    <SelectContent>
                      {Country.getAllCountries().map((c) => (
                        <SelectItem key={c.isoCode} value={c.name}>
                          {c.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="state"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>State</FormLabel>
                  <Select
                    value={field.value || ""}
                    onValueChange={(stateName) => {
                      // Store the state NAME in form
                      field.onChange(stateName);

                      // Find country code and state code for fetching cities
                      const countryCode = Country.getAllCountries().find(
                        (c) => c.name === form.getValues("country")
                      )?.isoCode;

                      const stateCode = permStates.find(
                        (s) => s.name === stateName
                      )?.isoCode;

                      if (countryCode && stateCode) {
                        const newCities = City.getCitiesOfState(
                          countryCode,
                          stateCode
                        );
                        setPermCities(newCities);
                        form.setValue("city", "");
                      }
                    }}
                  >
                    <SelectTrigger className="w-72">
                      <SelectValue placeholder="Select State" />
                    </SelectTrigger>
                    <SelectContent>
                      {permStates.map((s) => (
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

            <FormField
              control={form.control}
              name="city"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>City</FormLabel>
                  <Select
                    value={field.value || ""}
                    onValueChange={(cityName) => {
                      field.onChange(cityName);
                    }}
                  >
                    <SelectTrigger className="w-72">
                      <SelectValue placeholder="Select City" />
                    </SelectTrigger>
                    <SelectContent>
                      {permCities.map((c) => (
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

            <FormField
              control={form.control}
              name="district"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>District</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter District"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="taluka"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Taluka</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Taluka"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="nationlaity"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nationality</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Nationality"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Mobile / Religion / Eye Color */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="mobile_no"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Mobile No.</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Mobile No."
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="religion"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Religion</FormLabel>
                  <FormControl>
                    <Select
                      onValueChange={field.onChange}
                      value={field.value ?? ""}
                    >
                      <SelectTrigger className="w-72">
                        <SelectValue placeholder="Select Religion" />
                      </SelectTrigger>
                      <SelectContent>
                        {religions?.map((religion: string) => (
                          <SelectItem key={religion} value={religion}>
                            {religion}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="eye_colour"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Eye Color</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Eye Color"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Weight / DOB / Languages */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="weight"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Weight</FormLabel>

                  <div className="flex items-center gap-2">
                    {/* - button */}
                    <button
                      type="button"
                      className="px-3 py-1 border rounded"
                      onClick={() =>
                        field.onChange((Number(field.value) || 0) - 1)
                      }
                    >
                      -
                    </button>

                    {/* Input (arrow removed only here) */}
                    <div className="relative">
                      <Input
                        {...field}
                        type="number"
                        className="w-24 text-center
              [appearance:textfield]
              [&::-webkit-inner-spin-button]:appearance-none
              [&::-webkit-outer-spin-button]:appearance-none
            "
                      />
                    </div>

                    {/* + button */}
                    <button
                      type="button"
                      className="px-3 py-1 border rounded"
                      onClick={() =>
                        field.onChange((Number(field.value) || 0) + 1)
                      }
                    >
                      +
                    </button>
                  </div>

                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="language_known"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Languages Known</FormLabel>
                  <Popover>
                    <PopoverTrigger asChild>
                      <FormControl>
                        <button
                          type="button"
                          className="h-11 w-72 flex items-center justify-between rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 text-sm text-gray-700 dark:text-gray-300"
                        >
                          {Array.isArray(field.value) && field.value.length
                            ? field.value.join(", ")
                            : "Select Languages"}

                          <ChevronDown className="h-4 w-4 opacity-50" />
                        </button>
                      </FormControl>
                    </PopoverTrigger>
                    <PopoverContent align="start" className="w-72 p-3">
                      {[
                        "English",
                        "Hindi",
                        "Marathi",
                        "Gujarati",
                        "Telugu",
                        "Tamil",
                      ].map((item) => {
                        const isChecked =
                          Array.isArray(field.value) &&
                          field.value.includes(item);
                        return (
                          <label
                            key={item}
                            className="flex items-center gap-2 py-1 cursor-pointer text-sm"
                          >
                            <input
                              type="checkbox"
                              value={item}
                              checked={isChecked}
                              onChange={(e) => {
                                let updated = field.value
                                  ? [...field.value]
                                  : [];
                                if (e.target.checked) {
                                  updated.push(item);
                                } else {
                                  updated = updated.filter((v) => v !== item);
                                }
                                field.onChange(updated);
                              }}
                            />
                            {item}
                          </label>
                        );
                      })}
                    </PopoverContent>
                  </Popover>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="education_status"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Education Status</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Education Status"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Education / Identification / License Denied */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="visible_id_mark"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Identification Mark</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Identification Mark"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="blood_group"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Blood Group</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    value={field.value ?? ""}
                  >
                    <FormControl>
                      <SelectTrigger className="w-72">
                        <SelectValue placeholder="Select Blood Group" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {bloodGroups?.map((bloodGroup: string) => (
                        <SelectItem key={bloodGroup} value={bloodGroup}>
                          {bloodGroup}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Present Address */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="sameAsPermanent"
              checked={sameAsPermanent}
              onChange={(e) => handleSameAsPermanent(e.target.checked)}
              className="h-4 w-4"
            />
            <label
              htmlFor="sameAsPermanent"
              className="text-sm font-medium text-gray-700 cursor-pointer"
            >
              Same as Permanent Address
            </label>
          </div>

          <FormField
            control={form.control}
            name="present_address"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Present Address</FormLabel>
                <FormControl>
                  <Input {...field} placeholder="Enter Present Address" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="present_country"
              render={({ field }) => {
                // Find the country code from the stored country name
                const selectedCountryCode =
                  Country.getAllCountries().find((c) => c.name === field.value)
                    ?.isoCode || "";

                return (
                  <FormItem>
                    <FormLabel>Present Country</FormLabel>
                    <Select
                      value={selectedCountryCode}
                      onValueChange={(value) => {
                        onCountryChange(value);
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

            <FormField
              control={form.control}
              name="present_state"
              render={({ field }) => {
                // Find the state code from the stored state name
                const selectedStateCode =
                  presStates.find((s) => s.name === field.value)?.isoCode || "";

                return (
                  <FormItem>
                    <FormLabel>Present State</FormLabel>
                    <Select
                      value={selectedStateCode}
                      onValueChange={(value) => {
                        onStateChange(value);
                      }}
                      disabled={isReadOnly}
                    >
                      <SelectTrigger className="w-72">
                        <SelectValue placeholder="Select State" />
                      </SelectTrigger>
                      <SelectContent>
                        {presStates.map((s) => (
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
              name="present_city"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Present City</FormLabel>
                  <Select
                    value={field.value || ""}
                    onValueChange={(value) => {
                      onCityChange(value);
                    }}
                    disabled={isReadOnly}
                  >
                    <SelectTrigger className="w-72">
                      <SelectValue placeholder="Select City" />
                    </SelectTrigger>
                    <SelectContent>
                      {presCities.map((c) => (
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
          </div>

          {/* Present State / Domicile / Telephone / Mobile */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="present_district"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Present District</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Present District"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="present_taluka"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Present Taluka</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Present Taluka"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="domicile_state"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Domicile State</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Domicile State"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Language / Hair Color / Height */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="present_mobile_no"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Present Mobile No.</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Present Mobile No."
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="hair_colour"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Hair Color</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    value={field.value ?? ""}
                  >
                    <FormControl>
                      <SelectTrigger className="w-72">
                        <SelectValue
                          placeholder="Select Hair Color"
                          className="w-72"
                        />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {hairColors.map((color) => (
                        <SelectItem key={color} value={color}>
                          {color}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="height"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Height</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Height"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Birthplace / Blood Group / Profession */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="birth_place"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Birthplace</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Birth Place"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="present_profession"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Present Profession</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Present Profession"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="opening_balance"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Opening Balance</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Opening Balance"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Opening Balance / Date / Experience */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FormField
              control={form.control}
              name="opening_balance_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Opening Balance Date</FormLabel>
                  <FormControl>
                    <Input {...field} type="date" className="w-36" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="driving_exp"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Driving Experience</FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder="Enter Driving Experience"
                      className="w-72"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="martial_status"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Marital Status</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    value={field.value ?? ""}
                  >
                    <FormControl>
                      <SelectTrigger className="w-72">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="Single">Single</SelectItem>
                      <SelectItem value="Married">Married</SelectItem>
                      <SelectItem value="Divorced">Divorced</SelectItem>
                      <SelectItem value="Widowed">Widowed</SelectItem>
                      <SelectItem value="Separated">Separated</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          {/* Next Button */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            {!isReadOnly && (
              <Button
                type="submit"
                disabled={
                  addDriverBasics.isLoading || updateDriverBsics.isLoading
                }
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white"
              >
                {addDriverBasics.isLoading || updateDriverBsics.isLoading
                  ? "Saving..."
                  : mode === "edit"
                  ? "Update Basic"
                  : "Save Basic"}
              </Button>
            )}
          </div>
        </form>
      </Form>
    </div>
  );
};

export default DriverBasicForm;
