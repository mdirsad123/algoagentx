'use client'
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
import { usePoster, useUpdater, useFetcher, useDeleter } from "@/hooks/use-query";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Save, Trash2 } from "lucide-react";
import Cookies from "js-cookie";
import { useTranslation } from "@/hooks/use-translations";
import { DestinationSchema } from "@/schemas/destination-schema";
import { Destination } from "@/types/destination-type";
import Swal from "sweetalert2";
import { Country, State, City } from "country-state-city";
import type { IState, ICity } from "country-state-city";

type DestinationFormProps = {
  destination?: Destination;
  mode?: 'add' | 'edit' | 'view';
  readOnly?: boolean;
};

type FormInputs = z.infer<typeof DestinationSchema>;

const DestinationForm = ({
  destination,
  mode = 'add',
  readOnly = false,
}: DestinationFormProps) => {

  const param = useParams();
  const router = useRouter();
  const [loggedincompanyid] = useState(Cookies.get("loggedincompanyid"));
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));

  const {t, isRTL} = useTranslation();

  const form = useForm<FormInputs>({
    resolver: zodResolver(DestinationSchema),
    defaultValues: {
      dest_code: "",
      destination: "",
      country: "",
      state: "",
      city: "",
      companyid: Number(loggedincompanyid),
    },
  });

  const countries = Country.getAllCountries().filter((f) =>
  ["IN"].includes(f.isoCode)
);

// State management (already present)
const [states, setStates] = useState<IState[]>([]);
const [cities, setCities] = useState<ICity[]>([]);

// Replace the onCountryChange function:
const onCountryChange = (countryName: string) => {
  form.setValue("country", countryName);
  
  // Clear dependent fields
  form.setValue("state", "");
  form.setValue("city", "");
  
  // Find country code to load states
  const countryObj = countries.find(c => c.name === countryName);
  if (countryObj) {
    const stateList = State.getStatesOfCountry(countryObj.isoCode);
    setStates(stateList);
  } else {
    setStates([]);
  }
  setCities([]); // Clear cities when country changes
  
  // Clear errors
  if (form.formState.errors.country) {
    form.clearErrors("country");
  }
};

// Add the missing onStateChange function:
const onStateChange = (stateName: string) => {
  form.setValue("state", stateName);
  form.setValue("city", ""); // Clear city when state changes
  
  // Find country and state codes to load cities
  const countryName = form.getValues("country");
  const countryObj = countries.find(c => c.name === countryName);
  
  if (countryObj) {
    const stateObj = states.find(s => s.name === stateName);
    if (stateObj) {
      const cityList = City.getCitiesOfState(countryObj.isoCode, stateObj.isoCode);
      setCities(cityList);
    } else {
      setCities([]);
    }
  }
  
  // Clear errors
  if (form.formState.errors.state) {
    form.clearErrors("state");
  }
};

// Replace the onCityChange function:
const onCityChange = (cityName: string) => {
  form.setValue("city", cityName);
  
  // Clear errors
  if (form.formState.errors.city) {
    form.clearErrors("city");
  }
};

// Replace the setFormValue function:
const setFormValue = () => {
  if (!destination) {
    console.log("No destination data available");
    return;
  }

  console.log("Setting form values with:", destination);

  // Find country to load states
  const countryObj = countries.find(c => c.name === destination.country);
  
  if (countryObj) {
    const stateList = State.getStatesOfCountry(countryObj.isoCode);
    setStates(stateList);
    console.log("Loaded states for country:", destination.country, stateList);

    // Find state to load cities
    if (destination.state) {
      const stateObj = stateList.find(s => s.name === destination.state);
      
      if (stateObj) {
        const cityList = City.getCitiesOfState(countryObj.isoCode, stateObj.isoCode);
        setCities(cityList);
        console.log("Loaded cities for state:", destination.state, cityList);
      }
    }
  }

  // Reset form with all values including country, state, city
  const formValues = {
    dest_code: destination.dest_code ?? "",
    destination: destination.destination ?? "",
    country: destination.country ?? "",
    state: destination.state ?? "",
    city: destination.city ?? "",
    companyid: Number(loggedincompanyid),
  };
  
  console.log("Resetting form with values:", formValues);
  
  // Use setTimeout to ensure states and cities are set before form reset
  setTimeout(() => {
    form.reset(formValues);
    console.log("Form values after reset:", form.getValues());
  }, 100);
};

  const onSuccess = (response: Destination) => {
    Toast.fire({
      icon: "success",
      title: mode === 'edit' ? "Destination updated successfully" : "Destination added successfully",
    });
    
    form.reset();
    router.push("/master/destination");
  };
  
  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e?.response?.data?.message || "Submission Failed",
    });
  };

  const addDestination = usePoster("/destination/add", "DestinationList", onSuccess, onError);

  const updateDestination = useUpdater(
    `/destination/update/${destination?.destination_id || param["id"]}`,
    "destinationbyid",
    onSuccess,
    onError
  );

  const deleteDestination = useDeleter(
    "/destination/delete/",
    "DestinationList",
    () => {
      Toast.fire({
        icon: "success",
        title: "Destination deleted successfully",
      });
      router.push("/master/destination");
    },
    (err: any) => {
      Toast.fire({
        icon: "error",
        title: err?.response?.data?.message || "Delete Failed",
      });
    }
  );

  const onSubmit = (values: FormInputs) => {
    try {
      console.log(values);
      const currentDate = new Date();
      let data = { ...values };

      if ((mode === 'edit' && destination?.destination_id) || param["id"]) {
        data = {
          ...data,
          modified_on: currentDate,
          modified_by: Number(loggedinuserid),
          companyid: Number(loggedincompanyid),
        };
        updateDestination.mutate(data);
      } else {
        data = {
          ...data,
          created_by: Number(loggedinuserid),
          created_on: currentDate,
          companyid: Number(loggedincompanyid),
        };
        addDestination.mutate(data);
      }
    } catch (error) {
      console.log(error);
    }
  };

  const handleBack = () => {
    router.push("/master/destination");
  };

  const handleDelete = async () => {
    if (!destination?.destination_id && !param["id"]) {
      Toast.fire({
        icon: "error",
        title: "No record to delete",
      });
      return;
    }

    try {
      const result = await Swal.fire({
        title: "Are you sure?",
        text: "Do you want to delete this destination? This action cannot be undone.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        cancelButtonColor: "#3085d6",
        confirmButtonText: "Yes, delete it!",
        cancelButtonText: "No, cancel",
        reverseButtons: true
      });

      if (result.isConfirmed) {
        const idToDelete = destination?.destination_id || param["id"];
        deleteDestination.mutate(idToDelete);
      }
    } catch (error) {
      console.error("Error showing delete confirmation:", error);
      if (window.confirm("Are you sure you want to delete this destination?")) {
        const idToDelete = destination?.destination_id || param["id"];
        deleteDestination.mutate(idToDelete);
      }
    }
  };

  const isReadOnly = readOnly || mode === 'view';

  useEffect(() => {
  if (destination && destination.destination_id) {
    console.log("Destination changed, setting form values:", destination);
      setFormValue();
    }
  }, [destination, destination?.destination_id]);

  useEffect(() => {
    console.log(form.formState.errors);
  }, [form.formState.errors]);

  return (
    <div className="h-screen flex flex-col bg-white dark:bg-gray-900" dir={isRTL ? 'rtl' : 'ltr'}>
     
      <div className="px-6 py-4 flex-shrink-0">
        <Button
          type="button"
          variant="ghost"
          onClick={handleBack}
          className="mb-3 text-gray-700 dark:text-gray-300"
        >
          <ArrowLeft className={cn("w-4 h-4", isRTL ? "ml-2" : "mr-2")} />
          Back
        </Button>
      </div>

      {/* Dynamic Title */}
      <div className="px-6 pb-3">
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">
          {mode === "add"
            ? "Add Destination"
            : mode === "edit"
            ? "Edit Destination"
            : "View Destination"}
        </h2>

        <div className="mt-2 border-b border-gray-200 dark:border-gray-700" />
      </div>


      {/* Form Content */}
      <div className="flex-1 overflow-auto px-6 py-4">
        <div className="w-full">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            
            <div className="grid gap-6 md:grid-cols-3">
              
              {/* Destination Code */}
              <FormField
                control={form.control}
                name="dest_code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-200">
                      Destination Code <span className="text-red-500">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input 
                        placeholder="Enter Destination Code"
                        {...field}
                        maxLength={5}
                        value={field.value || ""}
                        readOnly={isReadOnly}
                        onChange={(e) => field.onChange(e.target.value.trimStart())}
                        className={cn(
                          "h-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100",
                          isReadOnly && "bg-gray-50 dark:bg-gray-600 cursor-not-allowed",
                          isRTL && "text-right"
                        )}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Destination */}
              <FormField
                control={form.control}
                name="destination"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-200">
                      Destination Name <span className="text-red-500">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input 
                        placeholder="Enter Destination"
                        {...field}
                        maxLength={200}
                        readOnly={isReadOnly}
                        onChange={(e) => field.onChange(e.target.value.trimStart())}
                        className={cn(
                          "h-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100",
                          isReadOnly && "bg-gray-50 dark:bg-gray-600 cursor-not-allowed",
                          isRTL && "text-right"
                        )}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

             {/* Country */}
            <FormField
              control={form.control}
              name="country"
              render={({ field, fieldState }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-200">
                    Country
                  </FormLabel>
                  <FormControl>
                    <Select
                      value={field.value || ""}
                      onValueChange={onCountryChange}
                      disabled={isReadOnly}
                    >
                      <SelectTrigger className={cn(
                        "h-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100",
                        isReadOnly && "bg-gray-50 dark:bg-gray-600 cursor-not-allowed opacity-60"
                      )}>
                        <SelectValue placeholder="Select Country" />
                      </SelectTrigger>
                      <SelectContent className="dark:bg-gray-800 dark:text-gray-200">
                        {countries.map(({ isoCode, name }) => (
                          <SelectItem key={isoCode} value={name}>
                            {name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                </FormItem>
              )}
            />

            {/* State */}
            <FormField
              control={form.control}
              name="state"
              render={({ field, fieldState }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-200">
                    State
                  </FormLabel>
                  <FormControl>
                    <Select
                      value={field.value || ""}
                      onValueChange={onStateChange}
                      disabled={isReadOnly || !form.watch("country")}
                    >
                      <SelectTrigger className={cn(
                        "h-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100",
                        (isReadOnly || !form.watch("country")) && "bg-gray-50 dark:bg-gray-600 cursor-not-allowed opacity-60"
                      )}>
                        <SelectValue placeholder="Select State" />
                      </SelectTrigger>
                      <SelectContent className="dark:bg-gray-800 dark:text-gray-200">
                        {states?.map(({ isoCode, name }) => (
                          <SelectItem key={isoCode} value={name}>
                            {name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                </FormItem>
              )}
            />

            {/* City */}
            <FormField
              control={form.control}
              name="city"
              render={({ field, fieldState }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-gray-700 dark:text-gray-200">
                    City
                  </FormLabel>
                  <FormControl>
                    <Select
                      value={field.value || ""}
                      onValueChange={onCityChange}
                      disabled={isReadOnly || !form.watch("state")}
                    >
                      <SelectTrigger className={cn(
                        "h-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100",
                        (isReadOnly || !form.watch("state")) && "bg-gray-50 dark:bg-gray-600 cursor-not-allowed opacity-60"
                      )}>
                        <SelectValue placeholder="Select City" />
                      </SelectTrigger>
                      <SelectContent className="dark:bg-gray-800 dark:text-gray-200">
                        {cities?.map(({ name }, i) => (
                          <SelectItem key={`${name}-${i}`} value={name}>
                            {name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                </FormItem>
              )}
            />


            </div>

            {/* Form Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              {!isReadOnly && (
                <Button
                  type="submit"
                  disabled={addDestination.isLoading || updateDestination.isLoading}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white"
                >
                  {addDestination.isLoading || updateDestination.isLoading ? "Saving..." : "Save"}
                </Button>
              )}
              <Button
                type="button"
                onClick={handleBack}
                className="px-4 py-2 bg-red-600 text-white"
              >
                Cancel
              </Button>
              
            </div>
          </form>
        </Form>
        </div>
      </div>
    </div>
  );
};

export default DestinationForm;