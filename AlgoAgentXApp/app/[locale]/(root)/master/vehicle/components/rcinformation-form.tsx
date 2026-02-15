"use client";
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import React, { useEffect, useState,useRef } from "react";
import { UseFormReturn } from "react-hook-form";
import { z } from "zod";
import { VehicleSchema } from "@/schemas/vehicle-schema";
import { Select } from "@/components/ui/select";
import { Country, State, City, IState, ICity } from "country-state-city";
import {
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";


type FormInputs = z.infer<typeof VehicleSchema>;

type Props = {
  form: UseFormReturn<FormInputs>;
  readOnly?: boolean;
};

const RcForm = ({ form, readOnly }: Props) => {
  // 🔹 Safe Number Handler (Prevents NaN)
  const handleNumberChange = (field: any, value: string) => {
    if (value === "") return field.onChange(null);  // empty → null

    const num = Number(value);
    if (!isNaN(num)) field.onChange(num);           // only valid numbers allowed
  };

   const countries = Country.getAllCountries().filter((f) =>
       ["IN"].includes(f.isoCode)
     );
   
     const [states, setStates] = useState<IState[]>([]);
     const [cities, setCities] = useState<ICity[]>([]);
   
   
      const onCountryChange = (code: string) => {
    form.setValue("country", code);
    form.setValue("state", "");
    form.setValue("city", "");

    const countryStates = State.getStatesOfCountry(code);
    setStates(countryStates);
    setCities([]);
  };

  // STATE CHANGE (stores NAME, uses ISO internally)
  const onStateChange = (stateName: string) => {
    const selectedState = states.find((s) => s.name === stateName);
    if (!selectedState) return;

    form.setValue("state", stateName);
    form.setValue("city", "");

    const list = City.getCitiesOfState("IN", selectedState.isoCode);
    setCities(list);
  };

  // ⭐ LOAD STATES & CITIES ON EDIT MODE
 // ⭐ LOAD STATES & CITIES AUTOMATICALLY IN EDIT MODE
useEffect(() => {
  const countryCode = form.getValues("country"); // "IN"
  const stateName = form.getValues("state");     // "Bihar"

  if (countryCode) {
    const st = State.getStatesOfCountry(countryCode); // <-- LOAD STATES
    setStates(st);

    if (stateName) {
      const selectedState = st.find((s) => s.name === stateName);
      if (selectedState) {
        const list = City.getCitiesOfState(countryCode, selectedState.isoCode);
        setCities(list); // <-- LOAD CITIES
      }
    }
  }
}, []);


  // Auto-load cities when state changes
  useEffect(() => {
    const stateName = form.getValues("state");

    if (!stateName) return;

    const selectedState = states.find((s) => s.name === stateName);
    if (!selectedState) return;

    const list = City.getCitiesOfState("IN", selectedState.isoCode);
    setCities(list);
  }, [states, form.watch("state")]);

   useEffect(() => {       //
          console.log(form.formState.errors);
        }, [form.formState.errors]);
  

  return (
    <>
     <div className={readOnly ? "pointer-events-none text-opacity-80 p-3" : ""}>
        {/* <div className="p-6 space-y-6"></div> */}
      <div className="grid lg:grid-cols-4 md:grid-cols-2 gap-6 mb-6">
        <FormField
          control={form.control}
          name="rc_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>R.C Name</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  className="h-9"
                  placeholder="Enter R.C name"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="rc_no"
          render={({ field }) => (
            <FormItem>
              <FormLabel>R.C Number</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  className="h-9"
                  placeholder="Enter R.C number"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>

      <div className="grid grid-cols-2 gap-6 mb-6">
        <FormField
          control={form.control}
          name="rc_address"
          render={({ field }) => (
            <FormItem>
              <FormLabel>R.C Address</FormLabel>
              <FormControl>
                <Textarea
                  {...field}
                  value={field.value ?? ""}
                  className="h-9"
                  placeholder="Enter R.C Address"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>

      <div className="grid lg:grid-cols-4 md:grid-cols-2 gap-6 mb-6">
                <FormField
                  control={form.control}
                  name="country"
                  render={({ field }) => (
                    
                      <FormItem>
                          <FormLabel >
                            Country
                          </FormLabel>
                          <FormControl>
                            <Select value={field.value || ""} onValueChange={(value) => {field.onChange(value);
                            onCountryChange(value);
                                }}
                              >
                              <SelectTrigger className="h-10">
                                <SelectValue placeholder= "Select Country" />
                              </SelectTrigger>
                              <SelectContent>
                                {countries.map((c) => (
                                <SelectItem key={c.isoCode} value={c.isoCode}>
                                  {c.name}
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
                  name="state"
                  render={({ field }) =>  (
                      
                      <FormItem>
                          <FormLabel>
                            State
                          </FormLabel>
                          <FormControl>
                           <Select                           
                          value={field.value || ""}
                              onValueChange={(value) => {
                                field.onChange(value);
                                onStateChange(value);   
                              }}
                            >
                              <SelectTrigger className="h-10">
                                <SelectValue placeholder="Select State" />
                              </SelectTrigger>
                              <SelectContent>
                               {states.map((s) => (
                                <SelectItem key={s.isoCode} value={s.name}>
                                  {s.name}
                                </SelectItem>
                              ))}
                              </SelectContent>
                            </Select>
                          </FormControl>
                        <FormMessage />
                      </FormItem>
                    )
                  }
                />
      
                <FormField
                  control={form.control}
                  name="city"
                  render={({ field }) => (
                      <FormItem>
                          <FormLabel >
                            City
                          </FormLabel>
                          <FormControl>
                          <Select
                          
                            value={field.value || ""}
                            onValueChange={field.onChange}
                          >
                            <SelectTrigger className="h-10">
                              <SelectValue placeholder="Select City" />
                            </SelectTrigger>
                            <SelectContent>
                             {cities.map((c) => (
                      <SelectItem key={c.name} value={c.name}>
                        {c.name}
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
                    name="district"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          District
                        </FormLabel>
                        <FormControl>
                          <Input
                            placeholder="District"
                            {...field}
                            value={field.value??""}
                            className="h-10"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />          
       </div>

      <div className="grid lg:grid-cols-5 md:grid-cols-3 gap-6 mb-6">
        <FormField
          control={form.control}
          name="laden_weight"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Laden Weight</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  value={field.value ?? ""}
                  onChange={(e) => handleNumberChange(field, e.target.value)}
                   onKeyDown={(e) => {
                    if (["e", "E", "+", "-",].includes(e.key)) {
                      e.preventDefault(); 
                    }
                  }}
                  placeholder="Enter Laden Weight"
                  className="h-9"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="unladen_weight"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Unladen Weight</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  value={field.value ?? ""}
                  onChange={(e) => handleNumberChange(field, e.target.value)}
                  placeholder="Enter Unladen Weight"
                  className="h-9"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="carry_capacity"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Carry Capacity</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  value={field.value ?? ""}
                  onChange={(e) => handleNumberChange(field, e.target.value)}
                  placeholder="Enter Carry Capacity"
                  className="h-9"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
         <FormField
          control={form.control}
          name="no_of_tyres"
          render={({ field }) => (
            <FormItem>
              <FormLabel>No. of Tyres</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  value={field.value ?? ""}
                  onChange={(e) => handleNumberChange(field, e.target.value)}
                  placeholder="Enter No. of Tyres"
                  className="h-9"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="vehicle_reg_date"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Vehicle Registration Date</FormLabel>
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
      </div>

      <div className="grid lg:grid-cols-5 md:grid-cols-3 gap-6 mb-6">
        <FormField
          control={form.control}
          name="start_kms"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Start Kilometers</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  value={field.value ?? ""}
                  onChange={(e) => handleNumberChange(field, e.target.value)}
                  placeholder="Enter Start KMS"
                  className="h-9"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="ending_kms"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Ending Kilometers</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  value={field.value ?? ""}
                  onChange={(e) => handleNumberChange(field, e.target.value)}
                  placeholder="Enter Ending KMS"
                  className="h-9"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      
        <FormField
          control={form.control}
          name="vehicle_type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Vehicle Type</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  placeholder="Enter Vehicle type"
                  className="h-9"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

       

        <FormField
          control={form.control}
          name="body_tank_fab"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Body/Tank Fab</FormLabel>
              <FormControl>
                <Input
                  {...field}
                  value={field.value ?? ""}
                  placeholder="Enter Body/Tank Fab"
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

export default RcForm;