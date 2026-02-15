"use client";

import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { supplierSchema } from "@/schemas/supplier-schema";
import { Country, State, City, IState, ICity } from "country-state-city";
import { useFetcher, usePoster, useUpdater } from "@/hooks/use-query";
import Toast from "@/components/shared/toast";
import { useRouter, useParams } from "next/navigation";


import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import Cookies from "js-cookie";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import CategoryForm from "../../category/components/category-form";


type FormInputs = z.infer<typeof supplierSchema>;
type SupplierFormProps = {
  supplier?: any;
  readOnly?: boolean;
};

const SupplierForm = ({supplier,readOnly}:SupplierFormProps) => {
  const param = useParams();
  const router = useRouter();
  const isEditMode = !!supplier;
  const isViewMode = readOnly;
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));
  const [showCategoryPopup, setShowCategoryPopup] = useState(false);
  const isInactive = isEditMode && supplier?.status === "Inactive";
  const isLocked = isViewMode || isInactive;

 const form = useForm<FormInputs>({
  resolver: zodResolver(supplierSchema),
  defaultValues: supplier
    ? {
        supplier_code: supplier.supplier_code,
        supplier_name: supplier.supplier_name,
        address: supplier.address,
        country: supplier.country,
        state: supplier.state,
        city: supplier.city,
        district: supplier.district,
        tax_percent: supplier.tax_percent,
        tax_type: supplier.tax_type,
        tan_no: supplier.tan_no,
        pan_no: supplier.pan_no,
        contact_person: supplier.contact_person,
        mobile_no: supplier.mobile_no,
        email: supplier.email,
        category: supplier.category,
        gst_no: supplier.gst_no,
        aadhar_no: supplier.aadhar_no,
        status: supplier.status,

        beneficiary_name: supplier.supplierbank?.beneficiary_name,
        beneficiary_account_no: supplier.supplierbank?.beneficiary_account_no,
        bank_name: supplier.supplierbank?.bank_name,
        bank_branch: supplier.supplierbank?.bank_branch,
        ifsc_code: supplier.supplierbank?.ifsc_code,
        
      }
    : undefined,
});

useEffect(() => {
  if (supplier) {
    form.reset({
      supplier_code: supplier.supplier_code,
      supplier_name: supplier.supplier_name,
      address: supplier.address,
      country: supplier.country,
      state: supplier.state,
      city: supplier.city,
      district: supplier.district,
      tax_percent: supplier.tax_percent,
      tax_type: supplier.tax_type,
      tan_no: supplier.tan_no,
      pan_no: supplier.pan_no,
      contact_person: supplier.contact_person,
      mobile_no: supplier.mobile_no,
      email: supplier.email,
      category: supplier.category,
      gst_no: supplier.gst_no,
      aadhar_no: supplier.aadhar_no,
       status: supplier.status,

      beneficiary_name: supplier.supplierbank?.beneficiary_name,
      beneficiary_account_no: supplier.supplierbank?.beneficiary_account_no,
      bank_name: supplier.supplierbank?.bank_name,
      bank_branch: supplier.supplierbank?.bank_branch,
      ifsc_code: supplier.supplierbank?.ifsc_code,
    });

    if (supplier.country) {
      const countryStates = State.getStatesOfCountry(supplier.country);
      setStates(countryStates);

      if (supplier.state) {
        const selectedState = countryStates.find((s) => s.name === supplier.state);
        if (selectedState) {
          const citiesList = City.getCitiesOfState(supplier.country, selectedState.isoCode);
          setCities(citiesList);
        }
      }
    }
  }
}, [supplier, form]);


  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = form;

  const countries = Country.getAllCountries().filter((f) =>
    ["IN"].includes(f.isoCode)
  );
  const [states, setStates] = useState<IState[]>([]);
  const [cities, setCities] = useState<ICity[]>([]);

  const onCountryChange = (isoCode: string) => {
    form.setValue("country", isoCode);
    form.setValue("state", "");
    form.setValue("city", "");

    const countryStates = State.getStatesOfCountry(isoCode);
    setStates(countryStates);
    setCities([]); 
  };

  const onStateChange = (stateName: string) => {
  const selectedState = states.find((s) => s.name === stateName);
  if (!selectedState) return;

  form.setValue("state", stateName);
  form.setValue("city", "");

  const citiesList = City.getCitiesOfState("IN", selectedState.isoCode);
  setCities(citiesList);
};


  useEffect(() => {
    const stateName = form.getValues("state");
    if (!stateName) {
      setCities([]);
      return;
    }

    const selectedState = states.find((s) => s.name === stateName);
    if (!selectedState) {
      setCities([]);
      return;
    }

    const list = City.getCitiesOfState("IN", selectedState.isoCode);
    setCities(list);
  }, [states, form.watch("state")]);
  

    const onSuccess = () => {
    Toast.fire({
      icon: "success",
      title: isEditMode ? "Supplier Updated Successfully!" : "Supplier Added Successfully!",
    });
    router.push("/master/supplier");
  };

  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e?.response?.data?.message || "Something went wrong",
    });
  };

  const addSupplier = usePoster("/supplier/add", "supplierList", onSuccess, onError);
  const updateSupplier = useUpdater(`/supplier/update/${param["id"]}`, "supplierbyid", onSuccess, onError);

  const onSubmit = (values: FormInputs) => {
    const userid = loggedinuserid ? Number(loggedinuserid) : undefined;

    if (!isEditMode) {
      addSupplier.mutate({
        ...values,
        created_by: userid,
        created_on: new Date().toISOString(),
        status:"Active"
      });
    } else {
      updateSupplier.mutate({
        ...values,
        modified_by: userid,
        modified_on: new Date().toISOString(),
      });
    }
  };

  const taxtypes = [
  { value: "code1", label: "Code 1" },
  { value: "code2", label: "Code 2" },
];

const headingText = isViewMode
    ? "View Supplier"
    : isEditMode
    ? "Edit Supplier"
    : "Add Supplier";


    const { data: CategoryList ,refetch:refetchcategory} = useFetcher(
      "/supplier/categorylist",
      "categorylistdropdown"
    );

     useEffect(() => {       //
        console.log(form.formState.errors);
      }, [form.formState.errors]);

    const PrintView = ({ data }: { data: any }) => {
      const categoryName =
    CategoryList?.find(
      (c: any) => c.category_id.toString() === data.category
    )?.category_name || "-";
    
      return (
      <div className="space-y-4 text-sm">
        <h1 className="text-xl font-semibold mb-4">View Supplier</h1>

        <div className="grid grid-cols-2 gap-4">
          <div><b>Supplier Code:</b> {data.supplier_code}</div>
          <div><b>Supplier Name:</b> {data.supplier_name}</div>
          <div><b>Status:</b> {data.status}</div>
        </div>

        <div>
          <b>Address:</b>
          <div className="mt-1">{data.address}</div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div><b>Country:</b> {data.country}</div>
          <div><b>State:</b> {data.state}</div>
          <div><b>City:</b> {data.city}</div>
          <div><b>District:</b> {data.district}</div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div><b>TAX Type:</b> {data.tax_type}</div>
          <div><b>TAX Percent:</b> {data.tax_percent}</div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div><b>PAN No:</b> {data.pan_no}</div>
          <div><b>TAN No:</b> {data.tan_no}</div>
          <div><b>GST No:</b> {data.gst_no}</div>
          <div><b>Aadhar No:</b> {data.aadhar_no}</div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div><b>Contact Person:</b> {data.contact_person}</div>
          <div><b>Email:</b> {data.email}</div>
          <div><b>Mobile No:</b> {data.mobile_no}</div>
        </div>

        <div>
          <div><b>Category:</b>{data.categoryName}</div>
        </div>

        <div>
          <h2 className="text-lg font-semibold mt-6">Bank Details</h2>
          <hr className="border-gray-300 mb-3" />

          <div className="grid grid-cols-2 gap-4">
            <div><b>Bank Name:</b> {data.bank_name}</div>
            <div><b>Beneficiary Name:</b> {data.beneficiary_name}</div>
            <div><b>Account No:</b> {data.beneficiary_account_no}</div>
            <div><b>Branch:</b> {data.bank_branch}</div>
            <div><b>IFSC Code:</b> {data.ifsc_code}</div>
          </div>
        </div>
      </div>
    );
    };

    const getCategoryName = (categoryId?: string | null) => {  
      if (!categoryId || !CategoryList) return "-";

      const found = CategoryList.find(
        (c: any) => c.category_id.toString() === categoryId
      );

      return found?.category_name || "-";
    };

    const handlePrint = () => {
      const printWindow = window.open("", "_blank", "width=900,height=700");
      if (!printWindow) return;

      const styles = Array.from(document.styleSheets)
        .map((sheet) => {
          try {
            return Array.from(sheet.cssRules).map(r => r.cssText).join("");
          } catch {
            return "";
          }
        })
        .join("");

      printWindow.document.open();
      printWindow.document.write(`
        <html>
          <head>
            <title>Supplier Details</title>
            <style>${styles}</style>
            <style>
              body { padding: 24px; background: white; }
            </style>
          </head>
          <body>
            ${document.getElementById("print-only-view")!.innerHTML}
          </body>
        </html>
      `);

      printWindow.document.close();
      printWindow.onload = () => {
        printWindow.print();
        printWindow.close();
      };
    };


    return (
      <>
        <Form {...form}>
          <div className="min-h-screen  p-3">
            <div className="bg-white ">
              
              {/* <div className="p-6 border-b border-gray-200">
                <button
                  onClick={() => router.push("/master/supplier")}
                  className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
                >
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Back
                </button>
                <h1 className="text-2xl font-semibold text-gray-900">{headingText}</h1>
              </div> */}

              {isInactive && !isViewMode && (
            <div className="mx-6 mt-4 p-3 rounded bg-yellow-100 text-yellow-800 text-sm">
              This supplier is <b>Inactive</b>. Editing is disabled.
            </div>
          )}

              <div className={isLocked ? "pointer-events-none opacity-80" : ""}>              
              <div className="p-6 space-y-6">
                <div className="grid lg:grid-cols-4 md:grid-cols-2 gap-6 ">
                    <FormField
                      control={form.control}
                      name="supplier_code"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel  className="text-gray-700">Supplier Code</FormLabel>
                          <FormControl>
                            <Input
                              {...field}
                              disabled={isEditMode} 
                            readOnly={isEditMode}
                              placeholder="Enter Supplier Code"
                              maxLength={20}
                            onChange={(e) =>field.onChange(e.target.value.trimStart())}/>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="supplier_name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-gray-700">Supplier Name <span className="text-red-500">*</span></FormLabel>
                          <FormControl>
                            <Input
                              {...field}
                              placeholder="Enter Supplier Name"
                              maxLength={100}
                            onChange={(e) =>field.onChange(e.target.value.trimStart())}/>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    {(isEditMode || isViewMode) && (
                      <FormField
                        control={form.control}
                        name="status"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel className=" text-gray-700">Status</FormLabel>
                            <FormControl>
                              <Input {...field} value={field.value ?? ""} disabled className="bg-gray-100" />
                            </FormControl>
                          </FormItem>
                        )}
                      />
                    )}
                  </div>

                  <FormField
                    control={form.control}
                    name="address"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-sm font-medium text-gray-700">Address</FormLabel>
                        <FormControl>
                          <Textarea
                            {...field}
                            value={field.value ?? ""}  
                            placeholder="Enter Full Address"
                            maxLength={200}
                            className="h-10 w-2/4"
                          onChange={(e) =>field.onChange(e.target.value.trimStart())}/>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />


            <div className="grid lg:grid-cols-4 md:grid-cols-2 gap-6 ">
              <FormField
                control={form.control}
                name="country"
                render={({ field }) => (
                  
                    <FormItem>
                        <FormLabel className="text-sm font-medium text-gray-700">
                          Country
                        </FormLabel>
                        <FormControl>
                          <Select value={field.value || ""} onValueChange={(value) => {field.onChange(value);
                          onCountryChange(value);
                              }}
                            >
                            <SelectTrigger className="h-10 text-left">
                              <SelectValue onBlur={field.onBlur} ref={field.ref} placeholder= "Select Country" />
                            </SelectTrigger>
                            <SelectContent>
                              {countries.map(({ isoCode, name }, i) => (
                                <SelectItem key={`${isoCode}${i}`} value={isoCode}>
                                  {name}
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
                  <FormLabel className="text-sm font-medium text-gray-700">
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
                        <SelectValue 
                         placeholder="Select State" />
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
                        <FormLabel className="text-sm font-medium text-gray-700">
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
                            {cities?.map((c, i) => (
                              <SelectItem key={i} value={c.name}>
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
                      <FormLabel className="text-sm font-medium text-gray-700">
                        District
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="District"
                          {...field}
                          maxLength={40} 
                          value={field.value??""}
                          className="h-10"
                        onChange={(e) =>field.onChange(e.target.value.trimStart())}/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />          
              </div>


                <div className="grid lg:grid-cols-4 md:grid-cols-3 gap-6">

                  <FormField
                    control={form.control}
                    name="tax_type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel  className="text-gray-700">TAX Type</FormLabel>
                        <FormControl>
                          <Select value={field.value ?? ""} onValueChange={field.onChange}>
                            <SelectTrigger><SelectValue placeholder="Select Tax Type" /></SelectTrigger>
                            <SelectContent>
                              {taxtypes.map((t) => (
                                <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
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
                    name="tax_percent"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel  className="text-gray-700">TAX Percentage</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            type="number"
                            value={field.value ?? ""}  
                            placeholder="Enter Percentage"
                            onChange={(e) => field.onChange(Number(e.target.value))}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="tan_no"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-gray-700">TAN No</FormLabel>
                        <FormControl>
                          <Input {...field} maxLength={10} value={field.value ?? ""}   placeholder="Enter TAN Number" 
                          onChange={(e) => {
                          field.onChange(e.target.value.replace(/\D/g, "")); 
                        }}/>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="pan_no"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-gray-700">PAN No</FormLabel>
                        <FormControl>
                          <Input {...field}  
                            maxLength={10} 
                            value={field.value ?? ""} 
                            placeholder="Enter PAN Number" 
                            onChange={(e) => field.onChange(e.target.value.trimStart().toUpperCase())}
                        />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                </div>

                <div className="grid lg:grid-cols-3 md:grid-cols-3 gap-6">
                <FormField
                  control={form.control}
                  name="contact_person"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-gray-700">Contact Person</FormLabel>
                      <FormControl>
                        <Input {...field} maxLength={40}  
                        value={field.value ?? ""}   
                        placeholder="Enter Contact Person"
                        onChange={(e) =>field.onChange(e.target.value.trimStart())}/>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                 
                  <FormField
                    control={form.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-gray-700">Email</FormLabel>
                        <FormControl>
                          <Input {...field} value={field.value ?? ""}  
                          maxLength={35}
                          placeholder="Enter Email" 
                          onChange={(e) =>field.onChange(e.target.value.trimStart())}/>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="mobile_no"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-gray-700">Mobile No</FormLabel>
                        <FormControl className="w-60">
                          <Input {...field} maxLength={10} value={field.value ?? ""}  placeholder="Enter Mobile Number"
                          onChange={(e) => {
                          field.onChange(e.target.value.replace(/\D/g, "")); 
                        }} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="grid lg:grid-cols-3 md:grid-cols-3 gap-6">
                  <FormField
                    control={form.control}
                    name="aadhar_no"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-gray-700">Aadhar No</FormLabel>
                        <FormControl>
                          <Input {...field} maxLength={12} value={field.value ?? ""}  placeholder="Enter Aadhar Number" 
                          onChange={(e) => {
                          field.onChange(e.target.value.replace(/\D/g, "")); 
                        }}/>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="gst_no"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-gray-700">GST No</FormLabel>
                        <FormControl>
                          <Input {...field} value={field.value ?? ""}   placeholder="Enter GST Number" 
                          onChange={(e) =>field.onChange(e.target.value.trimStart())}/>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                      control={form.control}
                      name="category"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-gray-700">Category</FormLabel>
                          <div className="flex items-center gap-2">
                          <FormControl>
                            <Select 
                              value={field.value ?? ""} 
                              onValueChange={field.onChange}
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="Select Category" />
                              </SelectTrigger>
                              <SelectContent>
                                {CategoryList?.map((item: any) => (
                                  <SelectItem key={item.category_id} value={item.category_id.toString()}>
                                    {item.category_name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </FormControl>
                          {!readOnly && (
                      <Button
                        type="button"
                        size="sm"
                        className="bg-blue-600 text-white"
                        onClick={() => setShowCategoryPopup(true)}
                      >
                        + Add
                      </Button>
                    )}
                    </div>

                    {showCategoryPopup && (
                      <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
                  <div className="bg-white rounded-md p-6 shadow-lg w-[600px]">
                          <CategoryForm
                          ispopup
                            onSuccessInline={(category) => {
                        setShowCategoryPopup(false);
                              refetchcategory()
                        if (category) {
                          form.setValue("category", category.category_id.toString());
                        }                  
                      }}
                      />
                        </div>
                      </div>
                      )}
                      <FormMessage />
                        </FormItem>
                      )}
                    />
                </div>

              <div>
                <h2 className="text-lg font-semibold mt-4 dark:text-gray-100">Bank Details</h2>
                <hr className="border-gray-300 dark:border-gray-700 mb-4" /> 

                <div className="grid lg:grid-cols-3 md:grid-cols-2 gap-6">

                  <FormField
                    control={form.control}
                    name="bank_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-gray-700">Bank</FormLabel>
                        <FormControl>
                          <Select value={field.value ?? ""} onValueChange={field.onChange}>
                            <SelectTrigger><SelectValue placeholder="Select Bank" /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="HDFC">HDFC Bank</SelectItem>
                              <SelectItem value="ICICI">ICICI Bank</SelectItem>
                              <SelectItem value="SBI">State Bank of India</SelectItem>
                            </SelectContent>
                          </Select>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="beneficiary_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-gray-700">Beneficiary Name</FormLabel>
                        <FormControl>
                          <Input {...field} value={field.value ?? ""}   placeholder="Enter Beneficiary Account" 
                          onChange={(e) =>field.onChange(e.target.value.trimStart())}/>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="beneficiary_account_no"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-gray-700">Beneficiary Account No</FormLabel>
                        <FormControl>
                          <Input {...field}maxLength={20}   value={field.value ?? ""}  placeholder="Enter Account Number" 
                        onChange={(e) => field.onChange(e.target.value.replace(/\D/g, ""))}/>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />              
              </div>

                <div className="grid lg:grid-cols-3 md:grid-cols-3 gap-6 mt-3">
                  <FormField
                    control={form.control}
                    name="bank_branch"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-gray-700">Branch</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            value={field.value ?? ""}  
                            maxLength={100}
                            placeholder="Enter Branch"
                            className="w-full px-3 py-2 border rounded-md"
                          onChange={(e) =>field.onChange(e.target.value.trimStart())}/>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="ifsc_code"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel className="text-gray-700">IFSC Code</FormLabel>
                        <FormControl>
                          <Input {...field} maxLength={40}  value={field.value ?? ""}  placeholder="Enter IFSC Code" 
                          onChange={(e) =>field.onChange(e.target.value.trimStart())}/>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  </div>
                </div>
              </div>
              </div>
              
                {!isViewMode && (
                  <div className="flex justify-end gap-4 p-4">
                    {!isInactive && (
                    <Button
                    type="submit" 
                    onClick={form.handleSubmit(onSubmit)}
                      className="bg-gray-800 text-white px-6 py-2 rounded-md">
                      {isEditMode ? "Update" : "Save"}
                    </Button>
                    )}
                    <Button type="button"  className="px-6 py-2 bg-red-600 text-white rounded-md"
                      onClick={() => router.push("/master/supplier")}
                    >
                      Cancel
                    </Button>
                  </div>
                )}
              {isViewMode && (
                <div className="flex justify-end gap-3 p-4">
                  <Button
                    type="button"
                    className="px-6 py-2 bg-blue-600 text-white rounded-md"
                    onClick={handlePrint}
                  >
                    Print
                  </Button>
                  <Button
                    type="button"
                    className="px-6 py-2 bg-red-600 text-white rounded-md"
                    onClick={() => router.push("/master/supplier")}
                  >
                    Close
                  </Button>
                </div>
              )}
          </div>
        </div>
    </Form>

    <div id="print-only-view" className="hidden">
      <PrintView data={{...form.getValues(),categoryName: getCategoryName(form.getValues("category")),
      }} />
    </div>
  </>
  );

};

export default SupplierForm;
