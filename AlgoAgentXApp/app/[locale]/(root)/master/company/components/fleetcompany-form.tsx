"use client";
import FormFooter from "@/components/shared/form-footer";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import React, { useEffect, useState,useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { date, z } from "zod";
import Toast from "@/components/shared/toast";
import { cn, getImageUrl } from "@/lib/utils";
import { CompanySchema } from "@/schemas/company-schema";
import { Company } from "@/types/company-type";
import { useRouter } from "next/navigation";
import { Select } from "@radix-ui/react-select";
import { useParams } from "next/navigation";
import DatePicker from "@/components/ui/date-picker";
import { Country, State, City, IState, ICity } from "country-state-city";
import { useFetcher, usePoster, usePosterWithFileUpload, useUpdater } from "@/hooks/use-query";
import Cookies from "js-cookie";
import { Textarea } from "@/components/ui/textarea";

type CompanyFormProps = {
  company?: Company;
  readOnly?: boolean;
};
type FormInputs = z.infer<typeof CompanySchema>;

const FleetCompanyForm = ({company,readOnly}: CompanyFormProps) => {
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));
  const router = useRouter();
  const param = useParams();
  const isEditMode = !!company;
  const isViewMode =  readOnly;
  const isInactive = isEditMode && company?.status === "Inactive";
  const isLocked = isViewMode || isInactive;
  const canPrint = isViewMode && company?.status === "Active";

  const [imageUrl, setImageUrl] = useState<string | null>(
    company?.company_logo || null
  );
  
  const [selectedLogoFile, setSelectedLogoFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const MAX_FILE_SIZE = 1 * 1024 * 1024;


  useEffect(() => {
    if (company?.company_logo) {
      setImageUrl(company.company_logo);
    } else {
      setImageUrl(null);
    }
    setSelectedLogoFile(null); 
  }, [company?.company_logo]);


  const countries = Country.getAllCountries().filter((f) =>
    ["IN"].includes(f.isoCode)
  );

  const [states, setStates] = useState<IState[]>([]);
  const [cities, setCities] = useState<ICity[]>([]);


  const onCountryChange = (e: string) => {
    const co = Country.getCountryByCode(e)?.name;
    form.setValue("country", e);
    form.setValue("state", "");
  form.setValue("city", "");     

    const countryStates = State.getStatesOfCountry(e);
    setStates(countryStates);
    setCities([]); // Clear cities
  };

 const onStateChange = (e: string) => {
  const selectedState = states.find((s) => s.isoCode === e);
  if (!selectedState) return;

  form.setValue("state", selectedState.name);
  form.setValue("city", "");

  const citiesList = City.getCitiesOfState("IN", e);
  setCities(citiesList);  
};

  const form = useForm<FormInputs>({
  resolver: zodResolver(CompanySchema),
  defaultValues: company
    ? {
        company_code: company.company_code ,
        company_name: company.company_name,
        address: company.address ,
        country: company.country,
        state: company.state ,
        city: company.city ,
        district: company.district ,
        
        tax_type: company.tax_type ,
        tax_percent: company.tax_percent ,

        tan_no: company.tan_no ,
        pan_no: company.pan_no ,
        tin_no: company.tin_no ,
        gst_no:company.gst_no,
        company_logo: company.company_logo ,

        registration_no: company.registration_no ,
        registration_date: company.registration_date ,

        status: company.status ,
      }
    : undefined,
});

 
 useEffect(() => {
  if (company) {
    form.reset({
      company_code: company.company_code ,
      company_name: company.company_name ,
      address: company.address ,
      country: company.country ,
      state: company.state ,
      city: company.city ,
      district: company.district ,

      tax_type: company.tax_type ,
      tax_percent: company.tax_percent ,

      tan_no: company.tan_no,
      pan_no: company.pan_no ,
      tin_no: company.tin_no ,
      gst_no:company.gst_no,
      company_logo: company.company_logo ,

      registration_no: company.registration_no,
      registration_date: company.registration_date,

      status: company.status,
    });

    if (company.country) {
        const countryStates = State.getStatesOfCountry(company.country);
        setStates(countryStates);

        if (company.state) {
          const selectedState = countryStates.find((s) => s.name === company.state);
          if (selectedState) {
            const citiesList = City.getCitiesOfState(company.country, selectedState.isoCode);
            setCities(citiesList);
          }
        }
      }
  }
}, [company,form]);


  const onSuccess = (response: Company) => {
    Toast.fire({
      icon: "success",
      title: param["id"]
        ? "Company updated Successfully!"
        : "Company Added Successfully!",
    });
    router.push("/master/company");
  };

  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e.response.data.message,
    });
  };

  const addCompany = usePosterWithFileUpload("/company/add", "companyList", onSuccess, onError,"POST");
  const updateCompany = usePosterWithFileUpload(
    `/company/update/${param["id"]}`,
    "companybyid",
    onSuccess,
    onError,
    "PUT"
  );


  const openFilePicker = () =>
    fileInputRef.current?.click();

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > MAX_FILE_SIZE) {
      Toast.fire({ icon: "error", title: "Image must be < 1MB" });
      return;
    }

    setSelectedLogoFile(file);
    setImageUrl(URL.createObjectURL(file));

  form.setValue("company_logo", "pending_upload", { shouldValidate: true });

  console.log("✅ Logo selected:", file.name);
};

const getFileNameFromUrl = (url?: string | null) => {
  if (!url) return "";
  return url.split("/").pop() || "";
};


const logoSrc = imageUrl
  ? imageUrl.startsWith("blob:")
    ? imageUrl
    : getImageUrl(imageUrl)
  : null;

const showUpload = !isViewMode && !isInactive;

const renderFileInfo = () => {
  if (!showUpload) return null;

  if (selectedLogoFile) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <span className="text-gray-700">{selectedLogoFile.name}</span>
        <span className="text-gray-500">
          ({(selectedLogoFile.size / 1024).toFixed(1)} KB)
        </span>
      </div>
    );
  }

  if (imageUrl) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <span>{getFileNameFromUrl(imageUrl)}</span>
        <span className="italic">(existing)</span>
      </div>
    );
  }

  return null;
};


const onSubmit = (values: FormInputs) => {
  try {

    if (!isEditMode) {
      const cleanedValues = Object.entries(values).reduce((acc, [key, val]) => {
       
        if (val !== undefined && val !== null && val !== "") {
          acc[key] = val;
        }
        return acc;
      }, {} as any);

         const  UserId =loggedinuserid ? Number(loggedinuserid) : undefined;

      const data = {
        ...cleanedValues,
        created_by: UserId,
        created_on: new Date().toISOString(), 
        status: "Active",
      };

      const formData = new FormData();
      
      const bodyString = JSON.stringify(data);
      formData.append("body", bodyString);

      if (selectedLogoFile) {
        formData.append("company_logo", selectedLogoFile);
      }

      addCompany.mutate(formData);
    }

else {
  const formData = new FormData();

  Object.entries(values).forEach(([key, val]) => {
    if (val === undefined || val === null || val === "") return;

    if (key === "tax_percent") {
      formData.append("tax_percent", Number(val).toString());
      return;
    }

    if (key === "registration_date") {
      formData.append("registration_date", new Date(val).toISOString());
      return;
    }

    formData.append(key, String(val));
  });


  const uid = loggedinuserid ? Number(loggedinuserid) : null;
  if (uid !== null && !isNaN(uid)) {
    formData.append("modified_by", uid.toString());
  }

  formData.append("modified_on", new Date().toISOString());

  if (selectedLogoFile) {
    formData.append("company_logo", selectedLogoFile);
  }

  updateCompany.mutate(formData);
}


  } catch (error) {
    console.error("❌ Form submission error:", error);
    Toast.fire({
      icon: "error",
      title: "Error submitting form",
    });
  }
};


  const taxtypes = [
  { value: "code1", label: "Code 1" },
  { value: "code2", label: "Code 2" },
];
const headingText = isViewMode
  ? "View Company"
  : isEditMode
    ? "Edit Company"
    : "Add Company";


     useEffect(() => {       //
        console.log(form.formState.errors);
      }, [form.formState.errors]);

      

    const PrintView = ({ data }: { data: any }) => (
      <div className="space-y-4">
        <h1 className="text-xl font-semibold mb-4">View Company</h1>

      <div className="grid grid-cols-2 gap-4">
        <div><b>Company Code:</b> {data.company_code}</div>
        <div><b>Company Name:</b> {data.company_name}</div>
        <div><b>Status:</b> {data.status}</div>
      </div>

        <div>
          <b>Company Logo:</b><br />
          {logoSrc && (
            <img src={logoSrc} className="w-20 h-20 mt-2" />
          )}
        </div>

        <div><b>Address:</b> {data.address}</div>

      <div className="grid grid-cols-2 gap-4">
        <div><b>Country:</b> {data.country}</div>
        <div><b>State:</b> {data.state}</div>
        <div><b>City:</b> {data.city}</div>
        <div><b>District:</b> {data.district}</div>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div><b>Tax Type:</b> {data.tax_type}</div>
        <div><b>Tax Percentage:</b> {data.tax_percent}</div>

        <div><b>Registration Date:</b> {data.registration_date}</div>
        <div><b>Registration No:</b> {data.registration_no}</div>

        <div><b>TAN No:</b> {data.tan_no}</div>
        <div><b>PAN No:</b> {data.pan_no}</div>
        <div><b>TIN No:</b> {data.tin_no}</div>
        <div><b>GST No:</b> {data.gst_no}</div>
      </div>
      </div>
    );

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
            <title>Company Details</title>
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
       <div className="min-h-screen p-3">
        <div className="max-w-full bg-white">
          {/* Header */}
          {/* <div className="p-6 border-b border-gray-200">
            <button 
            onClick={() => router.push("/master/company")}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>

          <h1 className="text-2xl font-semibold text-gray-900">
            {headingText}
          </h1>
          </div> */}

           {isInactive && !isViewMode && (
            <div className="mx-6 mt-4 p-3 rounded bg-yellow-100 text-yellow-800 text-sm">
              This company is <b>Inactive</b>. Editing is disabled.
            </div>
          )}

        <div className={isLocked ? "pointer-events-none opacity-80":""}>
          <div className="p-6 space-y-6">
            <div className="grid lg:grid-cols-4 md:grid-cols-2 gap-6">
              <FormField
                control={form.control}
                name="company_code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-medium text-gray-700">
                      Company Code
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Enter Company Code"
                        {...field}
                        disabled={isViewMode} 
                        readOnly={isEditMode} 
                        onChange={(e) =>field.onChange(e.target.value.trimStart())}
                        maxLength={20}
                        value={field.value ?? ""}
                        className="h-10"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="company_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-medium text-gray-700">
                      Company Name  <span className="text-red-500 ">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Enter Company Name"
                        {...field}
                        disabled={isViewMode}
                        onChange={(e) =>field.onChange(e.target.value.trimStart())}
                        value={field.value ?? ""}
                        className="h-10"
                      />
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
                    <FormLabel className="text-sm font-medium text-gray-700">Status</FormLabel>
                    <FormControl>
                      <Input {...field} disabled className="bg-gray-100 h-10" />
                    </FormControl>
                  </FormItem>
                )}
              />
            )}
          </div>

          <FormField
                control={form.control}
                name="company_logo"
                render={({ field }) => (
                  <FormItem>
                    <input type="hidden" {...field} />

                    <FormLabel className="text-sm font-medium text-gray-700">
                      Company Logo <span className="text-red-500">*</span>
                    </FormLabel>

                  <div className="space-y-3">
                    <div className="flex items-center gap-4">
                      {logoSrc ? (
                        <img
                          src={logoSrc}
                          alt="Company Logo"
                          className="w-20 h-20 rounded-md border object-cover"
                        />
                      ) : (
                        <div className="w-20 h-20 bg-gray-200 flex items-center justify-center text-sm rounded-md">
                          No Logo
                        </div>
                      )}

                      {showUpload ? (
                        <>
                          <input
                            type="file"
                            ref={fileInputRef}
                            className="hidden"
                            accept="image/*"
                            onChange={handleLogoChange}
                          />
                          <Button
                            type="button"
                            onClick={openFilePicker}
                            className="bg-blue-600 text-white px-4 py-2 rounded-md"
                          >
                            {selectedLogoFile ? "Change Logo" : "Upload Logo"}
                          </Button>
                        </>
                      ) : (
                        logoSrc && (
                        <a
                        href={getImageUrl(imageUrl)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 flex items-center gap-1"
                      >
                        👁 View logo
                      </a>
                        )
                      )}
                    </div>

                    {renderFileInfo()}
                  </div>

                  <FormMessage />
                </FormItem>
              )}
            />


            <FormField
              control={form.control}
              name="address"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-gray-700">
                    Address
                  </FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Enter Full Address"
                      maxLength={200}
                      {...field}
                      value={field.value ?? ""}
                      onChange={(e) =>field.onChange(e.target.value.trimStart())}
                      disabled={isViewMode}
                      className="h-10 w-2/4"
                    />
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
                  {/* <div className="flex items-center"> */}
                    <FormLabel className="text-sm font-medium text-gray-700">
                      Country
                    </FormLabel>
                    <FormControl>
                      <Select 
                      disabled={isViewMode}
                      value={field.value || ""} 
                      onValueChange={(value) => {field.onChange(value);
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
                  {/* </div> */}
                  <FormMessage />
                </FormItem>
                )}
          />

          <FormField
            control={form.control}
            name="state"
            render={({ field }) =>  (
                
                <FormItem>
                  {/* <div className="flex items-center"> */}
                    <FormLabel className="text-sm font-medium text-gray-700">
                      State
                    </FormLabel>
                    <FormControl>
                     <Select
                     disabled={isViewMode}
                      value={
                      states.find((s) => s.name === field.value)?.isoCode || ""
                    }
                        onValueChange={(value) => {
                          field.onChange(value);
                          onStateChange(value);   // update cities + reset city
                        }}
                        // disabled={!form.watch("country")} (it will show after country select)
                      >
                        <SelectTrigger className="h-10">
                          <SelectValue onBlur={field.onBlur} ref={field.ref} placeholder="Select State" />
                        </SelectTrigger>
                        <SelectContent>
                          {states?.map(({ isoCode, name }, i) => (
                            <SelectItem key={`${isoCode}${i}`} value={isoCode}>
                              {name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormControl>
                  {/* </div> */}
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
                  {/* <div className="flex items-center"> */}
                    <FormLabel className="text-sm font-medium text-gray-700">
                      City
                    </FormLabel>
                    <FormControl>
                    <Select
                      value={field.value || ""}
                      disabled={isViewMode}
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
                  {/* </div> */}
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
                      value={field.value??""}
                      maxLength={40}
                      onChange={(e) =>field.onChange(e.target.value.trimStart())}
                      disabled={isViewMode}
                      className="h-10"
                    />
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
                    <FormLabel className="text-sm font-medium text-gray-700">
                    TAX Type
                    </FormLabel>
                    <FormControl>
                     <Select
                    value={field.value??""}
                    disabled={isViewMode}
                    onValueChange={field.onChange}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Tax Type" />
                    </SelectTrigger>
                    <SelectContent>
                      {taxtypes.map((code) => (
                        <SelectItem key={code.value} value={code.value}>
                          {code.label}
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
                name="tax_percent"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-medium text-gray-700">
                      TAX Percentage
                    </FormLabel>
                    <FormControl>
                     <Input
                      placeholder="Enter Tax Percentage"
                      {...field}
                      type="number"
                      value={field.value ?? ""}
                      disabled={isViewMode}
                      onChange={(e) => {
                        const val = e.target.value;

                        if (val === "" || val === null) {
                          field.onChange(null); 
                          return;
                        }

                        field.onChange(Number(val));
                      }}
                      className="h-10"
                    />

                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="registration_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-medium text-gray-700">
                      Registration Date
                    </FormLabel>
                    <FormControl>
                     <input
                      type="date"
                      disabled={isViewMode}
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


              <FormField
                control={form.control}
                name="registration_no"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-medium text-gray-700">
                      Registration Number
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Enter Registration Number"
                        {...field}
                        value={field.value ?? ""}
                        onChange={(e) =>field.onChange(e.target.value.trimStart())}
                        disabled={isViewMode}
                        className="h-10"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            
            <div className="grid lg:grid-cols-4 md:grid-cols-3 gap-6">
              <FormField
                control={form.control}
                name="tan_no"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-medium text-gray-700">
                      TAN No
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Enter TAN No"
                        {...field}
                        value={field.value ?? ""}
                        disabled={isViewMode}
                        maxLength={10}
                        onChange={(e) =>
                          field.onChange(e.target.value.trimStart().toUpperCase())
                        }
                        className="h-10"
                      />
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
                    <FormLabel className="text-sm font-medium text-gray-700">
                      PAN No
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Enter PAN No"
                        {...field}
                        value={field.value ?? ""}
                        disabled={isViewMode}
                        maxLength={10}
                        onChange={(e) =>
                          field.onChange(e.target.value.trimStart().toUpperCase())
                        }
                        className="h-10"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
        
              <FormField
                control={form.control}
                name="tin_no"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-medium text-gray-700">
                      TIN No
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Enter TIN No"
                        {...field}
                         maxLength={11}
                         onChange={(e) =>
                            field.onChange(e.target.value.replace(/\D/g, ""))
                          }
                        value={field.value ?? ""}
                        disabled={isViewMode}
                        className="h-10"
                      />
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
                    <FormLabel className="text-sm font-medium text-gray-700">GST No</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        disabled={isViewMode}
                          value={field.value||""}
                          onChange={(e) =>field.onChange(e.target.value.trimStart())}
                        placeholder="Enter GST No"
                        className="h-10"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />   
            </div>
          </div>
       </div>     

      {!isViewMode && !isInactive && (
      <div className="flex  justify-end gap-4 p-4">
        <Button
          type="submit"
          onClick={form.handleSubmit(onSubmit)}
          className="px-6 py-2 bg-gray-800 text-white rounded-md"
        >
            {isEditMode ? "Update" : "Save"}
        </Button>
        <Button
          type="button"
          onClick={() => router.push("/master/company")}
          className="px-6 py-2 bg-red-600 text-white rounded-md"
        >
          Cancel
        </Button>
      </div>
      )}

       {!isViewMode && isInactive && (
        <div className="flex justify-end gap-3 p-4">
        <Button
          type="button"
          className="px-6 py-2 bg-red-600 text-white rounded-md"
          onClick={() => router.push("/master/company")}
        >
          Cancel
        </Button>
        </div>
      )}


      {isViewMode && (
        <div className="flex justify-end gap-3 p-4">
            {/* {canPrint && ( */}
            <Button
              type="button"
              className="px-6 py-2 bg-blue-600 text-white rounded-md"
              onClick={handlePrint}
            >
              Print
            </Button>
          {/* )} */}
          <Button
            type="button"
            className="px-6 py-2 bg-red-600 text-white rounded-md"
            onClick={() => router.push("/master/company")}
          >
            Close
          </Button>
        </div>
      )}         
      </div>
    </div>
    </Form>

<div id="print-only-view" className="hidden">
  <PrintView data={form.getValues()} />
</div>
</>
    
  );
};

export default FleetCompanyForm;