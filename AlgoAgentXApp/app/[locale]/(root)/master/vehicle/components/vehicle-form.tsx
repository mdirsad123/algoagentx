"use client";
import { Button } from "@/components/ui/button";
import { Form } from "@/components/ui/form";
import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Toast from "@/components/shared/toast";
import { useRouter } from "next/navigation";
import { useFetcher, usePoster, usePosterWithFileUpload, useUpdater, useUpdaterWithFileUpload } from "@/hooks/use-query";
import Cookies from "js-cookie";
import { VehicleDetails } from "@/types/vehicle-type";
import { VehicleSchema } from "@/schemas/vehicle-schema";
import VehicleForm from "./vehicleinformation-form";
import RcForm from "./rcinformation-form";
import InvoiceVehicleForm from "./invoiceinformation-form";
import { ChevronDown } from "lucide-react";
import VehicleDocumentsForm from "./vehicledocuments-form";
import VehiclemakeForm from "../../vehiclemake/components/vehiclemake-form";

type VehicleFormProps = {
  asDialog?: boolean;
  vehicle?: VehicleDetails;
  readOnly?: boolean;
  param?: any;
};
type FormInputs = z.infer<typeof VehicleSchema>;

const VehiclweForm = ({
  vehicle,
  asDialog,
  readOnly,
  param
}: VehicleFormProps) => {
  const [loggedinuserid] = useState(() => {
    const userId = Cookies.get("loggedinuserid");
    return userId;
  });
  
  const [existingFiles, setExistingFiles] = useState<{
    invoice_document?: string | null;
    rc_document?: string | null;
    insurance_document?: string | null;
  }>({});
  
  const router = useRouter();
  const isEditMode = !!vehicle;
  const isViewMode = readOnly;


  const [showMakeForm, setShowMakeForm] = useState(false);
  
const { data: VehicleMakeList, refetch: refetchVehicleMakeList } = useFetcher(
  "/vehicle/vehiclemakelist",
  "vehiclemakelist"
);

   const [openSection, setOpenSection] =
    useState<"vehicle" | "rc" | "invoice" |"documents" | null>("vehicle");

  const toggleSection = (name: "vehicle" | "rc" | "invoice" | "documents") => {
    setOpenSection((prev) => (prev === name ? null : name));
  };

  console.log("🎯 VehiclweForm - Vehicle data:", vehicle);

  const form = useForm<FormInputs>({
    resolver: zodResolver(VehicleSchema),
    defaultValues: {
      vehicle_no: "",
      make_id:"",
      vehicle_name: "",
      vehicle_model: "",
      year_mfg: undefined,
      chassis_no: "",
      engine_no: "",
      purchase_hire: "",
      dealer_name: "",
      purchase_inv_no: "",
      purchase_inv_amt: undefined,
      purchase_inv_date: undefined,
      cabin_fab_name: "",
      cabin_inv_no: "",
      cabin_inv_date: undefined,
      cabin_fab_amt: undefined,
      running_gear_fab_by: "",
      running_gear_inv_no: "",
      running_gear_inv_date: undefined,
      running_gear_fab_amt: undefined,
      rc_name: "",
      rc_address: "",
      rc_no: "",
       country: "",
      state: "",
      district: "",
      city: "",
      laden_weight: undefined,
      unladen_weight: undefined,
      carry_capacity: undefined,
      vehicle_reg_date: undefined,
      start_kms: undefined,
      ending_kms: undefined,
      vehicle_type: "",
      no_of_tyres: undefined,
      body_tank_fab: "",
      inv_no: "",
      inv_date: undefined,
      inv_amt: undefined,
      tank_no: "",
      sale_of_vehicle: undefined,
      sale_date: undefined,
      status: "Active",
      policy_no: "",
      policy_date: undefined,
      policy_amount: undefined,
      policy_expiry: undefined,
      status_updatedby: undefined,
      status_updatedon: undefined,
    },
  });

  const [isDataReady, setIsDataReady] = useState(false);


 useEffect(() => {
  if (vehicle && Object.keys(vehicle).length > 0) {
        
    const toDateOrNull = (date: any): Date | null | undefined => {
      if (!date) return null;
      if (date instanceof Date) return date;
      const parsed = new Date(date);
      return isNaN(parsed.getTime()) ? null : parsed;
    };

    const toNumberOrNull = (val: any): number | undefined => {
      if (val === null || val === undefined || val === "") return undefined;
      const num = Number(val);
      return isNaN(num) ? undefined : num;
    };

    setExistingFiles({
      invoice_document: vehicle.invoice_document,
      rc_document: vehicle.rc_document,
      insurance_document: vehicle.insurance_document,
    });

    // ✅ Convert make_id to string IMMEDIATELY
      const makeIdString = vehicle.make_id ? String(vehicle.make_id) : "";

      // ✅ Use setTimeout to ensure form is ready
      setTimeout(() => {
        // Set make_id FIRST with setValue for better control
        form.setValue("make_id", makeIdString, { 
          shouldValidate: false,
          shouldDirty: false,
          shouldTouch: false 
        });

        // Then reset the entire form
        form.reset({
          vehicle_no: vehicle.vehicle_no || "",
          make_id: makeIdString, 
          // vehicle_name: vehicle.vehicle_make?.vehicle_name || "",
          vehicle_model: vehicle.vehicle_model || "",
          year_mfg: toDateOrNull(vehicle.year_mfg),
          chassis_no: vehicle.chassis_no || "",
          engine_no: vehicle.engine_no || "",
          purchase_hire: vehicle.purchase_hire || "",
          dealer_name: vehicle.dealer_name || "",
          purchase_inv_no: vehicle.purchase_inv_no || "",
          purchase_inv_amt: toNumberOrNull(vehicle.purchase_inv_amt),
          purchase_inv_date: toDateOrNull(vehicle.purchase_inv_date),
          cabin_fab_name: vehicle.cabin_fab_name || "",
          cabin_inv_no: vehicle.cabin_inv_no || "",
          cabin_inv_date: toDateOrNull(vehicle.cabin_inv_date),
          cabin_fab_amt: toNumberOrNull(vehicle.cabin_fab_amt),
          running_gear_fab_by: vehicle.running_gear_fab_by || "",
          running_gear_inv_no: vehicle.running_gear_inv_no || "",
          running_gear_inv_date: toDateOrNull(vehicle.running_gear_inv_date),
          running_gear_fab_amt: toNumberOrNull(vehicle.running_gear_fab_amt),
          rc_name: vehicle.rc_name || "",
          rc_address: vehicle.rc_address || "",
          rc_no: vehicle.rc_no || "",
          country: vehicle.country || "",
          state: vehicle.state || "",
          district: vehicle.district || "",
          city: vehicle.city || "",
          laden_weight: toNumberOrNull(vehicle.laden_weight),
          unladen_weight: toNumberOrNull(vehicle.unladen_weight),
          carry_capacity: toNumberOrNull(vehicle.carry_capacity),
          vehicle_reg_date: toDateOrNull(vehicle.vehicle_reg_date),
          start_kms: toNumberOrNull(vehicle.start_kms),
          ending_kms: toNumberOrNull(vehicle.ending_kms),
          vehicle_type: vehicle.vehicle_type || "",
          no_of_tyres: toNumberOrNull(vehicle.no_of_tyres),
          body_tank_fab: vehicle.body_tank_fab || "",
          tank_no: vehicle.tank_no || "",
          sale_of_vehicle: toNumberOrNull(vehicle.sale_of_vehicle),
          sale_date: toDateOrNull(vehicle.sale_date),
          policy_no: vehicle.policy_no || "",
          policy_date: toDateOrNull(vehicle.policy_date),
          policy_amount: toNumberOrNull(vehicle.policy_amount),
          policy_expiry: toDateOrNull(vehicle.policy_expiry),
          status: vehicle.status || "Active",
          status_updatedby: toNumberOrNull(vehicle.status_updatedby),
          status_updatedon: toDateOrNull(vehicle.status_updatedon),
        }, {
          keepDefaultValues: false,
        });
        

        // ✅ Double-check and set again if needed
        const currentMakeId = form.getValues("make_id");
        if (!currentMakeId || currentMakeId !== makeIdString) {
          form.setValue("make_id", makeIdString);
        }

      }, 100); // Small delay to ensure form is ready
    }
  }, [vehicle, form]);


  const onSuccess = (response: VehicleDetails) => {
    Toast.fire({
      icon: "success",
      title: param["id"]
        ? "Vehicle updated Successfully!"
        : "Vehicle Added Successfully!",
    });
    router.push("/master/vehicle");
  };

  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e?.response?.data?.message || "Something went wrong!",
    });
  };

  const addVehicle = usePosterWithFileUpload("/Vehicle/add", "VehicleList", onSuccess, onError,"POST");
  const updateVehicle = usePosterWithFileUpload(
    `/Vehicle/update/${param?.id}`,
    "Vehiclebyid",
    onSuccess,
    onError,
    "PUT"
  );


   const onSubmit = (values: FormInputs) => {
  try {
   // ✅ VALIDATION
    if (!values.vehicle_no || values.vehicle_no.trim() === "") {
      Toast.fire({ icon: "error", title: "Vehicle No is required!" });
      return;
    }

    if (!values.make_id) {
      Toast.fire({ icon: "error", title: "Vehicle Make is required!" });
      return;
    }

    if (!loggedinuserid) {
      Toast.fire({ icon: "error", title: "User not logged in!" });
      return;
    }

    const today = new Date();
    const isUpdateMode = param?.id ? true : false;

    const toDate = (value: any) => {
      if (!value) return null;
      const date = new Date(value);
      return isNaN(date.getTime()) ? null : date;
    };

    // ✅ Check if there are NEW files to upload
    const hasNewFiles = 
      (values.invoice_document && values.invoice_document.length > 0) ||
      (values.rc_document && values.rc_document.length > 0) ||
      (values.insurance_document && values.insurance_document.length > 0);

    // ✅ ALWAYS use FormData for consistency (works for both create and update)
    const formData = new FormData();

    // Add all fields to FormData
    formData.append("vehicle_no", values.vehicle_no);
    formData.append("make_id", String(Number(values.make_id)));

    if (values.vehicle_model) formData.append("vehicle_model", values.vehicle_model);
    if (values.year_mfg) formData.append("year_mfg", toDate(values.year_mfg)?.toISOString() || "");
    if (values.chassis_no) formData.append("chassis_no", values.chassis_no);
    if (values.engine_no) formData.append("engine_no", values.engine_no);
    if (values.purchase_hire) formData.append("purchase_hire", values.purchase_hire);
    if (values.dealer_name) formData.append("dealer_name", values.dealer_name);
    if (values.purchase_inv_no) formData.append("purchase_inv_no", values.purchase_inv_no);
    if (values.purchase_inv_amt) formData.append("purchase_inv_amt", String(values.purchase_inv_amt));
    if (values.purchase_inv_date) formData.append("purchase_inv_date", toDate(values.purchase_inv_date)?.toISOString() || "");
    if (values.cabin_fab_name) formData.append("cabin_fab_name", values.cabin_fab_name);
    if (values.cabin_inv_no) formData.append("cabin_inv_no", values.cabin_inv_no);
    if (values.cabin_inv_date) formData.append("cabin_inv_date", toDate(values.cabin_inv_date)?.toISOString() || "");
    if (values.cabin_fab_amt) formData.append("cabin_fab_amt", String(values.cabin_fab_amt));
    if (values.running_gear_fab_by) formData.append("running_gear_fab_by", values.running_gear_fab_by);
    if (values.running_gear_inv_no) formData.append("running_gear_inv_no", values.running_gear_inv_no);
    if (values.running_gear_inv_date) formData.append("running_gear_inv_date", toDate(values.running_gear_inv_date)?.toISOString() || "");
    if (values.running_gear_fab_amt) formData.append("running_gear_fab_amt", String(values.running_gear_fab_amt));
    if (values.rc_name) formData.append("rc_name", values.rc_name);
    if (values.rc_address) formData.append("rc_address", values.rc_address);
    if (values.rc_no) formData.append("rc_no", values.rc_no);
    if (values.country) formData.append("country", values.country);
    if (values.state) formData.append("state", values.state);
    if (values.district) formData.append("district", values.district);
    if (values.city) formData.append("city", values.city);
    if (values.laden_weight) formData.append("laden_weight", String(values.laden_weight));
    if (values.unladen_weight) formData.append("unladen_weight", String(values.unladen_weight));
    if (values.carry_capacity) formData.append("carry_capacity", String(values.carry_capacity));
    if (values.vehicle_reg_date) formData.append("vehicle_reg_date", toDate(values.vehicle_reg_date)?.toISOString() || "");
    if (values.start_kms) formData.append("start_kms", String(values.start_kms));
    if (values.ending_kms) formData.append("ending_kms", String(values.ending_kms));
    if (values.vehicle_type) formData.append("vehicle_type", values.vehicle_type);
    if (values.no_of_tyres) formData.append("no_of_tyres", String(values.no_of_tyres));
    if (values.body_tank_fab) formData.append("body_tank_fab", values.body_tank_fab);
    if (values.inv_no) formData.append("inv_no", values.inv_no);
    if (values.inv_date) formData.append("inv_date", toDate(values.inv_date)?.toISOString() || "");
    if (values.inv_amt) formData.append("inv_amt", String(values.inv_amt));
    if (values.tank_no) formData.append("tank_no", values.tank_no);
    if (values.sale_of_vehicle) formData.append("sale_of_vehicle", String(values.sale_of_vehicle));
    if (values.sale_date) formData.append("sale_date", toDate(values.sale_date)?.toISOString() || "");
    if (values.policy_no) formData.append("policy_no", values.policy_no);
    if (values.policy_date) formData.append("policy_date", toDate(values.policy_date)?.toISOString() || "");
    if (values.policy_amount) formData.append("policy_amount", String(values.policy_amount));
    if (values.policy_expiry) formData.append("policy_expiry", toDate(values.policy_expiry)?.toISOString() || "");
    formData.append("status", values.status || "Active");

    // ✅ Add NEW files if uploaded
    if (values.invoice_document && values.invoice_document.length > 0) {
      formData.append("invoice_document", values.invoice_document[0]);
    }
    if (values.rc_document && values.rc_document.length > 0) {
      formData.append("rc_document", values.rc_document[0]);
    }
    if (values.insurance_document && values.insurance_document.length > 0) {
      formData.append("insurance_document", values.insurance_document[0]);
    }

    // ✅ Add audit fields
    if (isUpdateMode) {
      formData.append("modified_by", loggedinuserid);
      formData.append("modified_on", today.toISOString());
      updateVehicle.mutate(formData); // Use updateVehicle hook
    } else {
      formData.append("created_by", loggedinuserid);
      formData.append("created_on", today.toISOString());
      addVehicle.mutate(formData);
    }

  } catch (error) {
    Toast.fire({
      icon: "error",
      title: "Failed to submit form",
    });
  }
};


//  const onSubmit = (values: FormInputs) => {
//   try {
//     const isUpdate = Boolean(param?.id);
//     const formData = new FormData();

//     // Required validations
//     if (!values.vehicle_no?.trim()) {
//       return Toast.fire({ icon: "error", title: "Vehicle No is required!" });
//     }
//     if (!values.make_id) {
//       return Toast.fire({ icon: "error", title: "Vehicle Make is required!" });
//     }
//     if (!loggedinuserid) {
//       return Toast.fire({ icon: "error", title: "User not logged in!" });
//     }

//     const toDate = (d: any) => d ? new Date(d).toISOString() : "";

//     // Append form fields except file fields
//     Object.entries(values).forEach(([key, val]) => {
//       if (
//         key === "invoice_document" ||
//         key === "rc_document" ||
//         key === "insurance_document"
//       ) return;

//       if (val instanceof Date) {
//         formData.append(key, toDate(val));
//       } else if (val !== undefined && val !== null) {
//         formData.append(key, String(val));
//       }
//     });

//     // Append selected files
//     if (values.invoice_document?.[0]) {
//       formData.append("invoice_document", values.invoice_document[0]);
//     }
//     if (values.rc_document?.[0]) {
//       formData.append("rc_document", values.rc_document[0]);
//     }
//     if (values.insurance_document?.[0]) {
//       formData.append("insurance_document", values.insurance_document[0]);
//     }

//     // Audit fields & Status Handling
//     const today = new Date().toISOString();

//     if (isUpdate) {
//       // status from DB (NOT from form)
//       formData.append("status", vehicle?.status ? String(vehicle.status) : "Active");

//       formData.append("modified_by", loggedinuserid.toString());
//       formData.append("modified_on", today);
//       updateVehicle.mutate(formData);

//     } else {
//       // New entry → Always "N"
//       formData.append("status", "Active");

//       formData.append("created_by", loggedinuserid.toString());
//       formData.append("created_on", today);
//       addVehicle.mutate(formData);
//     }

//   } catch (error) {
//     console.error(error);
//     Toast.fire({ icon: "error", title: "Failed to submit form" });
//   }
// };

  

  const headingText = isViewMode
  ? "Vehicle Master"
  : isEditMode
    ? "Edit Vehicle Master"
    : "Add Vehicle Master";


     useEffect(() => {       //
        console.log(form.formState.errors);
      }, [form.formState.errors]);



    return (
      <>
      {showMakeForm && (
  <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
    <div className="bg-white rounded-md p-6 shadow-lg w-[600px]">

      <VehiclemakeForm
        readOnly={false}
        vehiclemake={null}
        isPopup={true} 
        onSuccessCallback={(newMake: any) => {
          setShowMakeForm(false);

          // Auto-refresh make list
          refetchVehicleMakeList();

          // Auto-select newly added make
          if (newMake?.make_id) {
            form.setValue("make_id", String(newMake.make_id));
          }
        }}
      />
    </div>
  </div>
)}

    <Form {...form}>
      <div className="min-h-screen  p-3">
        <div className="max-w-full mx-auto bg-white">

          {/* <div className="p-6 border-b border-gray-200">
          <button 
            onClick={() => router.push("/master/vehicle")}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>

            <h1 className="text-[22px] font-semibold text-gray-900">
             {headingText}
            </h1>
          </div> */}

          {/* Accordion Sections */}
          <form onSubmit={form.handleSubmit(onSubmit)}>

            {/* VEHICLE SECTION */}
            <div className="border-b">
              <div
                className="flex justify-between items-center px-4 py-3 cursor-pointer bg-gray-100"
                onClick={() => toggleSection("vehicle")}
              >
                <h2 className="font-semibold text-gray-700">Vehicle Information</h2>
                <ChevronDown
                  className={`transition-transform ${
                    openSection === "vehicle" ? "rotate-180" : ""
                  }`}
                />
              </div>
              {openSection === "vehicle" && (
                <div className="p-4">
                  <VehicleForm form={form} existingFiles={existingFiles} readOnly={isViewMode} setShowMakeForm={setShowMakeForm}/>
                </div>
              )}
            </div>

            {/* RC SECTION */}
            <div className="border-b">
              <div
                className="flex justify-between items-center px-4 py-3 cursor-pointer bg-gray-100"
                onClick={() => toggleSection("rc")}
              >
                <h2 className="font-semibold text-gray-700">RC Information</h2>
                <ChevronDown
                  className={`transition-transform ${
                    openSection === "rc" ? "rotate-180" : ""
                  }`}
                />
              </div>
              {openSection === "rc" && (
                <div className="p-4">
                  <RcForm form={form} readOnly={isViewMode} />
                </div>
              )}
            </div>

            {/* INVOICE SECTION */}
            <div className="border-b">
              <div
                className="flex justify-between items-center px-4 py-3 cursor-pointer bg-gray-100"
                onClick={() => toggleSection("invoice")}
              >
                <h2 className="font-semibold text-gray-700">Vehicle Invoice</h2>
                <ChevronDown
                  className={`transition-transform ${
                    openSection === "invoice" ? "rotate-180" : ""
                  }`}
                />
              </div>
              {openSection === "invoice" && (
                <div className="p-4">
                  <InvoiceVehicleForm form={form} readOnly={isViewMode} />
                </div>
              )}
            </div>

            {/* DOCUMENTS SECTION */}
<div className="border-b">
  <div
    className="flex justify-between items-center px-4 py-3 cursor-pointer bg-gray-100"
    onClick={() => toggleSection("documents")}
  >
    <h2 className="font-semibold text-gray-700">Document Upload</h2>
    <ChevronDown
      className={`transition-transform ${
        openSection === "documents" ? "rotate-180" : ""
      }`}
    />
  </div>

  {openSection === "documents" && (
    <div className="p-4">
      <VehicleDocumentsForm
        form={form}
        existingFiles={existingFiles}
        readOnly={isViewMode}
        isEditMode={isEditMode}
      />
    </div>
  )}
</div>


            {/* Footer buttons */}
            {!isViewMode && (
              <div className="flex justify-end gap-3 p-4">
                <Button type="submit" 
                className="bg-gray-800 text-white rounded-md px-6 py-2">
                  Save
                </Button>
                <Button 
                className="bg-red-600 text-white rounded-md px-6 py-2"
                 onClick={() => router.push("/master/vehicle")}>
                  Cancel
                </Button>
              </div>
            )}
            {isViewMode && (
              <div className="flex justify-end gap-3 p-4">
                <Button
                  type="button"
                  className="px-6 py-2 bg-red-600 text-white rounded-md"
                  onClick={() => router.push("/master/vehicle")}
                >
                  Close
                </Button>
              </div>
            )}
          </form>
        </div>
      </div>
    </Form>
    </>
  );
};

export default VehiclweForm;