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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useForm } from "react-hook-form";
import z from "zod";
import React, { useEffect, useState } from "react";
import Cookies from "js-cookie";
import { CustomerSchema } from "@/schemas/customer-schema";
import { Country, State, City, IState, ICity } from "country-state-city";
import { usePoster, useUpdater } from "@/hooks/use-query";
import Toast from "@/components/shared/toast";
import { useRouter, useParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { Textarea } from "@/components/ui/textarea";


type CompanyFormProps = {
  customer?: Customer;
  readOnly?: boolean;
};
type FormInputs = z.infer<typeof CustomerSchema>;
const CustomerForm =({customer,readOnly}:CompanyFormProps)=>{
  const param = useParams();
  const router = useRouter();
  const isEditMode = !!param["id"];
  const isViewMode = readOnly;
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));
  const isInactive = isEditMode && customer?.status === "Inactive";
  const isLocked = isViewMode || isInactive;


  const form = useForm<FormInputs>({
    resolver: zodResolver(CustomerSchema),
    defaultValues: customer
      ? {
          customer_code: customer.customer_code,
          customer_name: customer.customer_name,
          address: customer.address,
          country: customer.country,
          state: customer.state,
          city: customer.city,
          district: customer.district,
          pan_no: customer.pan_no,
          tin_no:customer.tin_no,
          contact_person: customer.contact_person,
          mobile_no: customer.mobile_no,
          email: customer.email,
          gst_no: customer.gst_no,
          aadhar_no: customer.aadhar_no,
          status: customer.status,

          beneficiary_name: customer.customerbank?.beneficiary_name,
          beneficiary_account_no: customer.customerbank?.beneficiary_account_no,
          bank_name: customer.customerbank?.bank_name,
          bank_branch: customer.customerbank?.bank_branch,
          ifsc_code: customer.customerbank?.ifsc_code,
        }
      : undefined,
  });
  
  useEffect(() => {
  if (!customer) return;

  form.reset({
    customer_code: "",
    customer_name: "",
    address: "",
    country: "",
    state: "",
    city: "",
    district: "",
    pan_no: "",
    tin_no: "",
    contact_person: "",
    mobile_no: "",
    email: "",
    gst_no: "",
    aadhar_no: "",
    status:"",

    beneficiary_name: "",
    beneficiary_account_no: "",
    bank_name: "",
    bank_branch: "",
    ifsc_code: "",
  });

  form.reset({
    customer_code: customer.customer_code ?? "",
    customer_name: customer.customer_name ?? "",
    address: customer.address ?? "",
    country: customer.country ?? "",
    state: customer.state ?? "",
    city: customer.city ?? "",
    district: customer.district ?? "",
    pan_no: customer.pan_no ?? "",
    tin_no: customer.tin_no ?? "",
    contact_person: customer.contact_person ?? "",
    mobile_no: customer.mobile_no ?? "",
    email: customer.email ?? "",
    gst_no: customer.gst_no ?? "",
    aadhar_no: customer.aadhar_no ?? "",
    status:customer.status ?? "",

    beneficiary_name: customer.customerbank?.beneficiary_name ?? "",
    beneficiary_account_no: customer.customerbank?.beneficiary_account_no ?? "",
    bank_name: customer.customerbank?.bank_name ?? "",
    bank_branch: customer.customerbank?.bank_branch ?? "",
    ifsc_code: customer.customerbank?.ifsc_code ?? "",
  });

  if (customer.country) {
    const countryStates = State.getStatesOfCountry(customer.country);
    setStates(countryStates);

    if (customer.state) {
      const selectedState = countryStates.find((s) => s.name === customer.state);
      if (selectedState) {
        const citiesList = City.getCitiesOfState(
          customer.country,
          selectedState.isoCode
        );
        setCities(citiesList);
      }
    }
  }

}, [customer]);


    const countries = Country.getAllCountries().filter((f) =>
      ["IN"].includes(f.isoCode)
    );
    const [states, setStates] = useState<IState[]>([]);
    const [cities, setCities] = useState<ICity[]>([]);
  
    const onCountryChange = (e: string) => {
      form.setValue("country", e);
      form.setValue("state", "");
      form.setValue("city", "");

    const countryStates = State.getStatesOfCountry(e);
      setStates(countryStates);
      setCities([]);
    };
  
    const onStateChange = (isoCode: string) => {
      const selectedState = states.find((s) => s.name === isoCode);
      if (!selectedState) return;
  
      form.setValue("state", isoCode);
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
        title: isEditMode ? "customer Updated Successfully!" : "customer Added Successfully!",
      });
      router.push("/master/customer");
    };
  
    const onError = (e: any) => {
      Toast.fire({
        icon: "error",
        title: e?.response?.data?.message || "Something went wrong",
      });
    };

 const addcustomer = usePoster("/customer/add", "customerList", onSuccess, onError);
   const updatecustomer = useUpdater(`/customer/update/${param["id"]}`, "customerbyid", onSuccess, onError);
 
   const onSubmit = (values: FormInputs) => {
     const userid = loggedinuserid ? Number(loggedinuserid) : undefined;
 
     if (!isEditMode) {
       addcustomer.mutate({
         ...values,
         created_by: userid,
         created_on: new Date().toISOString(),
         status:"Active"
       });
     } else {
       updatecustomer.mutate({
         ...values,
         modified_by: userid,
         modified_on: new Date().toISOString(),
       });
     }
   };

  const headingText = isViewMode
  ? "View Customer"
  : isEditMode
    ? "Edit Customer"
    : "Add Customer";

     useEffect(() => {
    console.log(form.formState.errors);
  }, [form.formState.errors]);

  const PrintView = ({ data }: { data: any }) => (
  <div className="space-y-4 text-sm">
    <h1 className="text-xl font-semibold mb-4">View Customer</h1>

    {/* BASIC DETAILS */}
    <div className="grid grid-cols-2 gap-4">
      <div><b>Customer Code:</b> {data.customer_code}</div>
      <div><b>Customer Name:</b> {data.customer_name}</div>
      <div><b>Status:</b> {data.status}</div>
    </div>

    {/* ADDRESS */}
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

    {/* TAX DETAILS */}
    <div className="grid grid-cols-2 gap-4">
      <div><b>PAN No:</b> {data.pan_no}</div>
      <div><b>TIN No:</b> {data.tin_no}</div>
      <div><b>GST No:</b> {data.gst_no}</div>
      <div><b>Aadhar No:</b> {data.aadhar_no}</div>
    </div>

    {/* CONTACT DETAILS */}
    <div className="grid grid-cols-2 gap-4">
      <div><b>Contact Person:</b> {data.contact_person}</div>
      <div><b>Email:</b> {data.email}</div>
      <div><b>Mobile No:</b> {data.mobile_no}</div>
    </div>

    {/* BANK DETAILS */}
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
            <title>Customer Details</title>
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
        <div className="bg-white ">

          {/* <div className="p-6 border-b border-gray-200">
            <button
              onClick={() => router.push("/master/customer")}
              className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back
            </button>

            <h1 className="text-2xl font-semibold text-gray-900">{headingText}</h1>
          </div> */}

          {isInactive && !isViewMode && (
            <div className="mx-6 mt-4 p-3 rounded bg-yellow-100 text-yellow-800 text-sm">
              This customer is <b>Inactive</b>. Editing is disabled.
            </div>
          )}

          <div className={isLocked  ? "pointer-events-none opacity-80" : ""}>
            <div className="p-6 space-y-6">

              <div className="grid lg:grid-cols-4 md:grid-cols-2 gap-6">
                <FormField
                  control={form.control}
                  name="customer_code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Customer Code</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          disabled={isEditMode}
                          readOnly={isEditMode}
                          placeholder="Enter Customer Code"
                          maxLength={20}
                          onChange={(e) => field.onChange(e.target.value.trimStart())}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="customer_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        Customer Name <span className="text-red-500">*</span>
                      </FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          placeholder="Enter Customer Name"
                          maxLength={40}
                          onChange={(e) => field.onChange(e.target.value.trimStart())}
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
                        <FormLabel >Status</FormLabel>
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
                    <FormLabel>Address</FormLabel>
                    <FormControl>
                      <Textarea
                        {...field}
                        placeholder="Enter Address"
                        maxLength={200}
                        value={field.value ?? ""}
                        onChange={(e) => field.onChange(e.target.value.trimStart())}
                        className="h-10 w-2/4"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid lg:grid-cols-4 md:grid-cols-2 gap-6">

                <FormField
                  control={form.control}
                  name="country"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Country</FormLabel>
                      <FormControl>
                        <Select
                          value={field.value || ""}
                          onValueChange={(v) => {
                            field.onChange(v);
                            onCountryChange(v);
                          }}
                        >
                          <SelectTrigger><SelectValue placeholder="Select Country" /></SelectTrigger>
                          <SelectContent>
                            {countries.map((c, i) => (
                              <SelectItem key={i} value={c.isoCode}>
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
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>State</FormLabel>
                      <FormControl>
                        <Select
                          value={field.value || ""}
                          onValueChange={(iso) => {
                            field.onChange(iso);
                            onStateChange(iso);
                          }}
                        >
                          <SelectTrigger><SelectValue placeholder="Select State" /></SelectTrigger>
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
                  )}
                />

                <FormField
                  control={form.control}
                  name="city"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>City</FormLabel>
                      <FormControl>
                        <Select
                          value={field.value || ""}
                          onValueChange={field.onChange}
                        >
                          <SelectTrigger><SelectValue placeholder="Select City" /></SelectTrigger>
                          <SelectContent>
                            {cities.map((c, i) => (
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
                      <FormLabel>District</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          maxLength={40}
                          placeholder="Enter District"
                          value={field.value ?? ""}
                          onChange={(e) =>
                            field.onChange(e.target.value.trimStart())
                          }
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
                  name="pan_no"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>PAN No</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          maxLength={10}
                          value={field.value ?? ""}
                          onChange={(e) =>
                            field.onChange(
                              e.target.value.trimStart().toUpperCase()
                            )
                          }
                          placeholder="Enter PAN No"
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
                      <FormLabel>TIN No</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          maxLength={11}
                          value={field.value ?? ""}
                          placeholder="Enter TIN No"
                          onChange={(e) =>
                            field.onChange(e.target.value.replace(/\D/g, ""))
                          }
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
                      <FormLabel>GST No</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          maxLength={35}
                          value={field.value ?? ""}
                          placeholder="Enter GST No"
                          onChange={(e) =>
                            field.onChange(e.target.value.trimStart())
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="aadhar_no"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Aadhar No</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          maxLength={12}
                          value={field.value ?? ""}
                          placeholder="Enter Aadhar Number"
                          onChange={(e) =>
                            field.onChange(e.target.value.replace(/\D/g, ""))
                          }
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
                      <FormLabel>Contact Person</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          maxLength={40}
                          value={field.value ?? ""}
                          placeholder="Enter Contact Person"
                          onChange={(e) =>
                            field.onChange(e.target.value.trimStart())
                          }
                        />
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
                      <FormLabel>Email</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          maxLength={40}
                          value={field.value ?? ""}
                          placeholder="Enter Email"
                          onChange={(e) =>
                            field.onChange(e.target.value.trimStart())
                          }
                        />
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
                      <FormLabel>Mobile No</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          maxLength={10}
                          value={field.value ?? ""}
                          placeholder="Enter Mobile Number"
                          onChange={(e) =>
                            field.onChange(e.target.value.replace(/\D/g, ""))
                          }
                          className="w-60"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div>
                <h2 className="text-lg font-semibold mt-4">Bank Details</h2>
                <hr className="border-gray-300 mb-4" />

                <div className="grid lg:grid-cols-3 md:grid-cols-2 gap-6">
                  {/* Bank */}
                  <FormField
                    control={form.control}
                    name="bank_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Bank</FormLabel>
                        <FormControl>
                          <Select
                            value={field.value ?? ""}
                            onValueChange={field.onChange}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select Bank" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="HDFC">HDFC Bank</SelectItem>
                              <SelectItem value="ICICI">ICICI Bank</SelectItem>
                              <SelectItem value="SBI">
                                State Bank of India
                              </SelectItem>
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
                        <FormLabel>Beneficiary Name</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            placeholder="Enter Beneficiary"
                            value={field.value ?? ""}
                            onChange={(e) =>
                              field.onChange(e.target.value.trimStart())
                            }
                          />
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
                        <FormLabel>Beneficiary Account No</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            maxLength={20}
                            placeholder="Enter Account Number"
                            value={field.value ?? ""}
                            onChange={(e) =>
                              field.onChange(e.target.value.replace(/\D/g, ""))
                            }
                          />
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
                        <FormLabel>Bank Branch</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            maxLength={100}
                            placeholder="Enter Branch"
                            value={field.value ?? ""}
                            onChange={(e) =>
                              field.onChange(e.target.value.trimStart())
                            }
                          />
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
                        <FormLabel>IFSC Code</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            maxLength={40}
                            placeholder="Enter IFSC Code"
                            value={field.value ?? ""}
                            onChange={(e) =>
                              field.onChange(e.target.value.trimStart())
                            }
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              </div>
            </div>
          </div>

          {!isViewMode && !isInactive && (
            <div className="flex justify-end gap-4 p-4">
              <Button
                type="submit"
                onClick={form.handleSubmit(onSubmit)}
                className="bg-gray-800 text-white px-6 py-2 rounded-md"
              >
              {isEditMode ? "Update" : "Save"}
              </Button>

              <Button
                type="button"
                className="px-6 py-2 bg-red-600 text-white rounded-md"
                onClick={() => router.push("/master/customer")}
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
              onClick={() => router.push("/master/customer")}
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
                onClick={() => router.push("/master/customer")}
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

export default CustomerForm;