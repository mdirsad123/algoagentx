'use client'
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import React from "react";
import { useForm } from "react-hook-form";

const HireSlipDetails = () => {
  const form = useForm({
    defaultValues: {
      hireSlipNo: "",
      hireSlipDate: "",
      status: "",
      bookingNo: "",
      bookingDate: "",
      customer: "",
      company: "",
      destinationFrom: "",
      destinationTo: "",
      vehicle: "",
      supplier: "",
      productName: "",
      description: ""
    },
  });

  const handleClose = () => {
    console.log("Close clicked");
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-950 p-6">
      <div className="w-full px-6 py-4">
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow-lg">

          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Hire Slip Details
            </h1>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xl leading-none"
            >
              ✕
            </button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">

            {/* Hire Slip Info Row */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">
                  Hire slip No.
                </label>
                <Input
                  readOnly
                  value=""
                  className="h-9 text-sm bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-700"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">
                  Hire Slip Date
                </label>
                <Input
                  type="date"
                  value=""
                  className="h-9 w-36 text-sm border-gray-300 dark:border-gray-700"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">
                  Status
                </label>
                <Select disabled>
                  <SelectTrigger className="h-9 text-sm border-gray-300 dark:border-gray-700">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                </Select>
              </div>
            </div>

            {/* Booking History Section */}
            <div className="space-y-4">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                Booking History
              </h2>

              {/* Booking Details Subsection */}
              <div>
                <h3 className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Booking Details
                </h3>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">
                      Booking No.
                    </label>
                    <Select disabled>
                      <SelectTrigger className="h-9 text-sm">
                        <SelectValue placeholder="Select booking" />
                      </SelectTrigger>
                    </Select>
                  </div>

                  <div>
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">
                      Booking Date
                    </label>
                    <Input
                      type="date"
                      value=""
                      className="h-9 w-36 text-sm"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">
                      Customer
                    </label>
                    <Input
                      value=""
                      readOnly
                      className="h-9 text-sm bg-gray-50 dark:bg-gray-800"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">
                      Company
                    </label>
                    <Select disabled>
                      <SelectTrigger className="h-9 text-sm">
                        <SelectValue placeholder="Select company" />
                      </SelectTrigger>
                    </Select>
                  </div>

                  <div>
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">
                      Destination From
                    </label>
                    <Input
                      value=""
                      readOnly
                      className="h-9 text-sm bg-gray-50 dark:bg-gray-800"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">
                      Destination To
                    </label>
                    <Input
                      value=""
                      readOnly
                      className="h-9 text-sm bg-gray-50 dark:bg-gray-800"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">
                      Vehicle
                    </label>
                    <Select disabled>
                      <SelectTrigger className="h-9 text-sm">
                        <SelectValue placeholder="Select vehicle" />
                      </SelectTrigger>
                    </Select>
                  </div>

                  <div>
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">
                      Supplier
                    </label>
                    <Input
                      value=""
                      readOnly
                      className="h-9 text-sm bg-gray-50 dark:bg-gray-800"
                    />
                  </div>
                </div>
              </div>

              {/* Product / Package Details Section */}
              <div>
                <h3 className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Product / Package Details
                </h3>

                <div className="space-y-3">
                  <div>
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">
                      Product Name
                    </label>
                    <Input
                      placeholder="Enter Product Name"
                      className="h-9 text-sm"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-medium text-gray-600 dark:text-gray-400 block mb-1.5">
                      Description
                    </label>
                    <textarea
                      placeholder="Enter Description"
                      className="w-full h-20 text-sm p-2 border rounded border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* History Section (kept same, since it's not part of form values) */}
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                History
              </h2>

              <div className="border rounded-lg overflow-hidden">
                <div className="grid grid-cols-5 bg-gray-100 dark:bg-gray-800 border-b">
                  <div className="p-2 text-xs font-medium text-gray-600 dark:text-gray-400 border-r">Slip</div>
                  <div className="p-2 text-xs font-medium text-gray-600 dark:text-gray-400 border-r">Status</div>
                  <div className="p-2 text-xs font-medium text-gray-600 dark:text-gray-400 border-r">Status Updated on</div>
                  <div className="p-2 text-xs font-medium text-gray-600 dark:text-gray-400 border-r">Status Updated By</div>
                  <div className="p-2 text-xs font-medium text-gray-600 dark:text-gray-400">Status Updated Remark</div>
                </div>

                {/* Example rows kept because they are static */}
                <div className="grid grid-cols-5 border-b">
                  <div className="p-2 text-xs">1</div>
                  <div className="p-2 text-xs">Booked</div>
                  <div className="p-2 text-xs">16/10/2025 10:16 AM</div>
                  <div className="p-2 text-xs">Operations Team</div>
                  <div className="p-2 text-xs">Vehicle assigned and loading in progress</div>
                </div>
              </div>
            </div>

          </div>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              onClick={handleClose}
              className="h-9 px-6 text-sm bg-gray-900 dark:bg-gray-700 text-white"
            >
              Close
            </Button>
          </div>

        </div>
      </div>
    </div>
  );
};

export default HireSlipDetails;
