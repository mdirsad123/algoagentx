"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { Country, State, City, IState, ICity } from "country-state-city";

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

import { usePoster, useDeleter } from "@/hooks/use-query";
import Toast from "@/components/shared/toast";
import { DriverBasic } from "@/types/driver-type";
import { DriverColumns } from "../columns";
import { RotateCcw } from "lucide-react";
import Swal from "sweetalert2";

type Props = {
  driverList: DriverBasic[];
};



const DriverTable = ({ driverList }: Props) => {
  const router = useRouter();

  /* ---------------- FORM ---------------- */
  const form = useForm<DriverBasic>({
    defaultValues: {
      driver_name: "",
      mobile_no: "",
      email: "",
      country: "",
      state: "",
      city: "",
      status: "",
    },
  });

  /* ---------------- STATE ---------------- */
  const [driverData, setDriverData] = useState<DriverBasic[]>(driverList);
  const [selectedCountry, setSelectedCountry] = useState<string>("");
  const [selectedState, setSelectedState] = useState<string>("");
  const [states, setStates] = useState<IState[]>([]);
  const [cities, setCities] = useState<ICity[]>([]);

  // Get all countries
  const countries = Country.getAllCountries();

  // Handle country change
  useEffect(() => {
    if (selectedCountry) {
      const countryStates = State.getStatesOfCountry(selectedCountry);
      setStates(countryStates);
      setCities([]);
      setSelectedState("");
      form.setValue("state", "");
      form.setValue("city", "");
    } else {
      setStates([]);
      setCities([]);
    }
  }, [selectedCountry, form]);

  // Handle state change
  useEffect(() => {
    if (selectedCountry && selectedState) {
      const stateCities = City.getCitiesOfState(selectedCountry, selectedState);
      setCities(stateCities);
      form.setValue("city", "");
    } else {
      setCities([]);
    }
  }, [selectedState, selectedCountry, form]);

  /* ---------------- SEARCH API ---------------- */
  const searchDrivers = usePoster(
    "/driver/driver-list",
    "driverList",
    (data: DriverBasic[]) => {
      setDriverData(data);
    },
    (err: any) => {
      Toast.fire({
        icon: "error",
        title: err?.response?.data?.message || "Failed to fetch drivers",
      });
    }
  );

  /* ---------------- DELETE API ---------------- */
  const deleteDriver = useDeleter(
    "/driver/delete/",
    "driverList",
    () => {
      Swal.fire("Deleted!", "Driver deleted successfully.", "success");
      searchDrivers.mutate(form.getValues());
    },
    (err: any) => {
      Swal.fire(
        "Error!",
        err?.response?.data?.message || "Delete failed",
        "error"
      );
    }
  );

  /* ---------------- SUBMIT ---------------- */
  const onSearch = (values: DriverBasic) => {
    // Filter out empty strings and undefined values
    const filters: Record<string, string> = {};
    
    if (values.driver_name && values.driver_name.trim()) {
      filters.driver_name = values.driver_name.trim();
    }
    if (values.mobile_no && values.mobile_no.trim()) {
      filters.mobile_no = values.mobile_no.trim();
    }
    if (values.email && values.email.trim()) {
      filters.email = values.email.trim();
    }
    if (values.country && values.country !== "__select__") {
      filters.country = values.country;
    }
    if (values.state && values.state !== "__select__") {
      filters.state = values.state;
    }
    if (values.city && values.city !== "__select__") {
      filters.city = values.city;
    }
    if (values.status && values.status !== "__select__") {
      filters.status = values.status;
    }

    console.log("Searching with filters:", filters);
    searchDrivers.mutate(filters);
  };

  /* ---------------- RESET ---------------- */
  const handleReset = () => {
    form.reset({
      driver_name: "",
      mobile_no: "",
      email: "",
      country: "",
      state: "",
      city: "",
      status: "",
    });
    setSelectedCountry("");
    setSelectedState("");
    setStates([]);
    setCities([]);
    setDriverData(driverList);
  };

  /* ---------------- ROW ACTIONS ---------------- */
  const handleRowView = (row: DriverBasic) => {
    router.push(`/master/driver/${row.driver_id}`);
  };

  const handleRowEdit = (row: DriverBasic) => {
    router.push(`/master/driver/edit/${row.driver_id}`);
  };

  const handleDelete = async (item: DriverBasic) => {
    const res = await Swal.fire({
      title: "Are you sure?",
      text: "Do you want to delete this driver?",
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Delete",
      cancelButtonText: "Cancel",
    });

    if (res.isConfirmed) {
      deleteDriver.mutate(item.driver_id);
    }
  };

  return (
    <div className="p-5 space-y-4">
      {/* 🔍 FILTER FORM */}
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSearch)}
          className="grid grid-cols-1 md:grid-cols-4 gap-3"
        >
          {/* DRIVER NAME - INPUT */}
          <FormField
            control={form.control}
            name="driver_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Driver Name</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    value={field.value || ""}
                    placeholder="Enter driver name"
                    className="h-11"
                  />
                </FormControl>
              </FormItem>
            )}
          />

          {/* MOBILE NUMBER - INPUT */}
          <FormField
            control={form.control}
            name="mobile_no"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Mobile Number</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    value={field.value || ""}
                    placeholder="Enter mobile number"
                    className="h-11"
                  />
                </FormControl>
              </FormItem>
            )}
          />

          {/* EMAIL - INPUT */}
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    value={field.value || ""}
                    type="text"
                    placeholder="Enter email"
                    className="h-11"
                  />
                </FormControl>
              </FormItem>
            )}
          />

          {/* COUNTRY - DROPDOWN */}
          <FormField
            control={form.control}
            name="country"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Country</FormLabel>
                <Select
                  value={field.value || "__select__"}
                  onValueChange={(v) => {
                    const val = v === "__select__" ? "" : v;
                    field.onChange(val);
                    setSelectedCountry(val);
                  }}
                >
                  <FormControl>
                    <SelectTrigger className="h-11">
                      <SelectValue placeholder="--Select Country--" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent className="max-h-[200px]">
                    <SelectItem value="__select__">--Select--</SelectItem>
                    {countries.map((country) => (
                      <SelectItem key={country.isoCode} value={country.isoCode}>
                        {country.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormItem>
            )}
          />

          {/* STATE - DROPDOWN */}
          <FormField
            control={form.control}
            name="state"
            render={({ field }) => (
              <FormItem>
                <FormLabel>State</FormLabel>
                <Select
                  value={field.value || "__select__"}
                  onValueChange={(v) => {
                    const val = v === "__select__" ? "" : v;
                    field.onChange(val);
                    setSelectedState(val);
                  }}
                  disabled={!selectedCountry}
                >
                  <FormControl>
                    <SelectTrigger className="h-11">
                      <SelectValue placeholder="--Select State--" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent className="max-h-[200px]">
                    <SelectItem value="__select__">--Select--</SelectItem>
                    {states.length > 0 ? (
                      states.map((state) => (
                        <SelectItem key={state.isoCode} value={state.isoCode}>
                          {state.name}
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="__none__" disabled>
                        No states available
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </FormItem>
            )}
          />

          {/* CITY - DROPDOWN */}
          <FormField
            control={form.control}
            name="city"
            render={({ field }) => (
              <FormItem>
                <FormLabel>City</FormLabel>
                <Select
                  value={field.value || "__select__"}
                  onValueChange={(v) => field.onChange(v === "__select__" ? "" : v)}
                  disabled={!selectedState}
                >
                  <FormControl>
                    <SelectTrigger className="h-11">
                      <SelectValue placeholder="--Select City--" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent className="max-h-[200px]">
                    <SelectItem value="__select__">--Select--</SelectItem>
                    {cities.length > 0 ? (
                      cities.map((city) => (
                        <SelectItem key={city.name} value={city.name}>
                          {city.name}
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="__none__" disabled>
                        No cities available
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </FormItem>
            )}
          />

          {/* BUTTONS */}
          <div className="flex items-end gap-2">
            <button
              type="submit"
              className="h-11 flex-1 rounded-md bg-primary text-white font-medium hover:bg-primary/90 transition-colors"
              disabled={searchDrivers.isLoading}
            >
              {searchDrivers.isLoading ? "Searching..." : "Search"}
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
        columns={DriverColumns({
          onView: handleRowView,
          onEdit: handleRowEdit,
          onDelete: handleDelete,
        })}
        data={driverData}
        showPagination
        showSearch={true}
        paginationOptions={{ showRowCount: true, showPageSize: true }}
        exportOptions={{
          pdf: true,
          csv: true,
          filename: "Driver List",
          title: "Driver List",
        }}
      />
    </div>
  );
};

export default DriverTable;