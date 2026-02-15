"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { DataTable } from "@/components/shared/data-table";
import {
  Form,
  FormField,
  FormItem,
  FormControl,
  FormLabel,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";

import { useFetcher, usePoster } from "@/hooks/use-query";
import Toast from "@/components/shared/toast";
import { Destination } from "@/types/destination-type";
import { DestinationColumns } from "../columns";
import { RotateCcw } from "lucide-react";
import { Country, State, City } from "country-state-city";
import type { IState, ICity } from "country-state-city";

type Props = {
  destinationList: Destination[];
};

const DestinationTable = ({ destinationList }: Props) => {
  const router = useRouter();

  /* ---------------- FORM ---------------- */
  const form = useForm<Partial<Destination>>({});

  const [destinationsData, setDestinationData] = useState<Destination[]>(destinationList);

  /* ---------------- STATE ---------------- */

  /* ---------------- DROPDOWNS ---------------- */
  // const { data: countryData } = useFetcher(
  //   "/master/destination/countries",
  //   "countryDropdown"
  // );

  // const { data: stateData } = useFetcher(
  //   "/master/destination/states",
  //   "stateDropdown"
  // );

  // const { data: cityData } = useFetcher(
  //   "/master/destination/cities",
  //   "cityDropdown"
  // );

  const { data: destinationData } = useFetcher(
      "/destination/destinationdropdown",
      "destinationdropdown"
    );

  const countries = Country.getAllCountries().filter((f) =>
    ["IN"].includes(f.isoCode)
  );

  // State management (already present)
  const [states, setStates] = useState<IState[]>([]);
  const [cities, setCities] = useState<ICity[]>([]);

  const onCountryChange = (countryName: string) => {
    form.setValue("country", countryName);

    // Clear dependent fields
    form.setValue("state", "");
    form.setValue("city", "");

    // Find country code to load states
    const countryObj = countries.find((c) => c.name === countryName);
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
    const countryObj = countries.find((c) => c.name === countryName);

    if (countryObj) {
      const stateObj = states.find((s) => s.name === stateName);
      if (stateObj) {
        const cityList = City.getCitiesOfState(
          countryObj.isoCode,
          stateObj.isoCode
        );
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

  /* ---------------- SEARCH API ---------------- */
 
  /* ---------------- RESET ---------------- */
  const handleReset = () => {
    form.reset({
      dest_code: undefined,
      destination: undefined,
      country: undefined,
      state: undefined,
      city: undefined,
    });
    setDestinationData(destinationList);
  };

  /* ---------------- ROW ACTIONS ---------------- */
  const handleRowView = (row: Destination) => {
    router.push(`/master/destination/${row.destination_id}`);
  };

  const handleRowEdit = (row: Destination) => {
    router.push(`/master/destination/edit/${row.destination_id}`);
  };

  const handleRowDelete = (row: Destination) => {
    // Implement delete logic
    console.log("Delete destination:", row);
  };

  return (
    <div className="p-5 space-y-4">
      {/* 🔍 FILTER FORM */}
      <Form {...form}>
        <form
          // onSubmit={form.handleSubmit(onSearch)}
          className="grid grid-cols-1 md:grid-cols-6 gap-3"
        >
          {/* DESTINATION */}
          <FormField
            control={form.control}
            name="destination_id"
            render={({ field }) => (
              <FormItem>
                
                <Select
                  value={field.value ? String(field.value) : "__select__"}
                  onValueChange={(v) =>
                    field.onChange(v === "__select__" ? undefined : Number(v))
                  }
                >
                  <FormControl>
                    <SelectTrigger className="h-11">
                      <SelectValue placeholder="--Select--" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    <SelectItem value="__select__">--Select--</SelectItem>
                    {destinationData?.destination?.length ? (
                      destinationData.destination.map((d: any) => (
                        <SelectItem
                          key={d.destination_id}
                          value={String(d.destination_id)}
                        >
                          {d.destination}
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="__none__" disabled>
                        No destinations found
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </FormItem>
            )}
          />

          {/* COUNTRY */}
          <FormField
            control={form.control}
            name="country"
            render={({ field, fieldState }) => (
              <FormItem>
                
                <FormControl>
                  <Select
                    value={field.value || ""}
                    onValueChange={onCountryChange}
                  >
                    <SelectTrigger
                      className={
                        "h-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      }
                    >
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
                
                <FormControl>
                  <Select
                    value={field.value || ""}
                    onValueChange={onStateChange}
                  >
                    <SelectTrigger
                      className={
                        "h-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      }
                    >
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
                
                <FormControl>
                  <Select
                    value={field.value || ""}
                    onValueChange={onCityChange}
                  >
                    <SelectTrigger
                      className={
                        "h-10 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      }
                    >
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
          {/* BUTTONS */}
          <div className="flex items-end gap-2">
            <button
              type="submit"
              className="h-11 flex-1 rounded-md bg-primary text-white font-medium hover:bg-primary/90 transition-colors"
              // disabled={searchDestinations.isLoading}
            >
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="h-11 w-11 rounded-md bg-gray-200 hover:bg-gray-300 transition-colors flex items-center justify-center"
              title="Reset filters"
            >
              <RotateCcw className="h-4 w-4 text-gray-700" />
            </button>
          </div>
        </form>
      </Form>

      {/* 📋 TABLE */}
      <DataTable
        columns={DestinationColumns({
          onView: handleRowView,
          onEdit: handleRowEdit,
          onDelete: handleRowDelete,
        })}
        data={destinationsData}
        showPagination
        paginationOptions={{ showRowCount: true, showPageSize: true }}
        exportOptions={{
          pdf: true,
          csv: true,
          filename: "Destination List",
          title: "Destination List",
        }}
      />
    </div>
  );
};

export default DestinationTable;
