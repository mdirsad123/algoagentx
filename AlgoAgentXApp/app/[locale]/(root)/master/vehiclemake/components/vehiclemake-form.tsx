"use client";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormField,
  FormItem,
  FormControl,
  FormLabel,
  FormMessage
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import Toast from "@/components/shared/toast";
import { z } from "zod";
import Cookies from "js-cookie";
import { useRouter, useParams } from "next/navigation";
import { VehiclemakeSchema } from "@/schemas/vehiclemake-schema";
import { usePoster, useUpdater } from "@/hooks/use-query";

type FormInputs = z.infer<typeof VehiclemakeSchema>;

type vehiclemakeProps = {
  vehiclemake?: any;
  readOnly?: boolean;
   onSuccessCallback?: (data: any) => void;
   isPopup?: boolean;
};

const VehiclemakeForm = ({ vehiclemake, readOnly = false ,onSuccessCallback ,isPopup}: vehiclemakeProps) => {
  const param = useParams();
  const router = useRouter();
  // const isEditMode = !!param["id"];
  const isEditMode = !isPopup && !!param["id"]; 
  const isViewMode = readOnly;

  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));

  const form = useForm<FormInputs>({
    resolver: zodResolver(VehiclemakeSchema),
    defaultValues: vehiclemake
  ? {
      vehicle_code: vehiclemake.vehicle_code ?? "",
      vehicle_name: vehiclemake.vehicle_name ?? "",
      description: vehiclemake.description ?? ""
    }
  : {
      vehicle_code: "",
      vehicle_name: "",
      description: ""
    }

  });

  useEffect(() => {
    if (vehiclemake) {
      form.reset({
        vehicle_code: vehiclemake.vehicle_code,
        vehicle_name: vehiclemake.vehicle_name,
        description: vehiclemake.description
      });
    }
  }, [vehiclemake,form]);

  const onSuccess = (res:any) => {
    Toast.fire({
      icon: "success",
      title: isEditMode
        ? "Vehiclemake Updated Successfully!"
        : "Vehiclemake Added Successfully!"
    });

  if (isPopup && onSuccessCallback) {
    onSuccessCallback(res.data);   
    return; 
  }

  if (!isPopup) {
    router.push("/master/vehiclemake"); 
  }
  };

  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e?.response?.data?.message || "Something went wrong"
    });
  };

  const addCategory = usePoster(
    "/vehiclemake/add",
    "VehicleList",
    onSuccess,
    onError
  );

  const updateCategory = useUpdater(
    `/vehiclemake/update/${param["id"]}`,
    "vehiclebyid",
    onSuccess,
    onError
  );


  const onSubmit = (values: FormInputs) => {
    const UserId = loggedinuserid ? Number(loggedinuserid) : undefined;

    if (!isEditMode || isPopup) {
      const data = {
        ...values,
        created_by: UserId,
        created_on: new Date().toISOString()
      };
      addCategory.mutate(data);
    } else {
      const data = {
        ...values,
        modified_by: UserId,
        modified_on: new Date().toISOString()
      };
      updateCategory.mutate(data);
    }
  };

  const headingText = isViewMode
    ? "View Vehiclemake"
    : isEditMode
    ? "Edit Vehiclemake"
    : "Add Vehiclemake";

     useEffect(() => {       //
        console.log(form.formState.errors);
      }, [form.formState.errors]);

 return (
  <Form {...form}>
    <div className={isPopup ? "p-4" : "min-h-screen p-3"}>
      <div className={isPopup ? "bg-white p-4  max-w-lg mx-auto" : "bg-white rounded-lg shadow-sm"}>        

        <div className={readOnly ? "pointer-events-none opacity-80" : ""}>
          <div className={isPopup ? "space-y-4" : "p-6 space-y-6"}>
            <div className={isPopup ? "grid grid-cols-1 gap-4" : "grid lg:grid-cols-[220px_280px_550px] md:grid-cols-2 gap-6"}>

              <FormField
                control={form.control}
                name="vehicle_code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Vehicle Code</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        placeholder="Enter Vehicle Code"
                        disabled={isEditMode}
                        readOnly={isEditMode}
                        className="h-10"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="vehicle_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-800">Vehicle Name <span className="text-red-500">*</span></FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        disabled={isViewMode}
                        placeholder="Enter Vehicle Name"
                        className="h-10"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        value={field.value ?? ""}
                        disabled={isViewMode}
                        placeholder="Enter Description"
                        className="h-10"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

            </div>
          </div>

            {!readOnly && (
              <div className="flex justify-end gap-4 pt-4">
                <Button
                  type="submit"
                  className="px-6 py-2 bg-gray-800 text-white rounded-md"
                  onClick={form.handleSubmit(onSubmit)}
                >
                  {isEditMode ? "Update" : "Save"}
                </Button>
                  <Button
                    type="button"
                    className="px-6 py-2 bg-red-600 text-white rounded-md"
                     onClick={() => {
                      if (isPopup) {
                        onSuccessCallback?.(null);
                      } else {
                        router.push("/master/vehiclemake");
                      }
                    }}
                  >                                    
                    Cancel
                  </Button>
                  </div>
                )}

                {isViewMode && (
                  <div className="flex justify-end gap-3 p-4">
                  <Button
                    type="button"
                    className="px-6 py-2 bg-red-600 text-white rounded-md"
                    onClick={() => router.push("/master/vehiclemake")}

                  >
                    Close
                  </Button>
                  </div>
                )} 
              </div>
          </div>
        </div>

  </Form>
);

};

export default VehiclemakeForm;
