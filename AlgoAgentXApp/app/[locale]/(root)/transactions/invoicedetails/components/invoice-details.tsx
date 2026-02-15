'use client'
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import React, { useState } from "react";

const InvoiceHistory = () => {
  const [formData, setFormData] = useState({
    invoiceNo: "129403583867",
    invoiceDate: "2025-10-28",
    status: "Acknowledged",
    invoiceFor: "Greenfield Agro Traders",
    invoiceAmount: "₹67,500.00",
    customer: "Greenfield Agro Traders",
    destinationFrom: "Pune, Maharashtra",
    productName: "Guns and Roses",
    description: "Full truck load delivery of Organic Fertilizer from Pune to Chennai. Goods dispatched safely and in good condition."
  });

  const [historyData] = useState([
    {
      slNo: 1,
      status: "Generated",
      updatedOn: "15/10/2025 10:15 AM",
      updatedBy: "Rahul Singh",
      remark: "Vehicle assigned and loading in progress"
    },
    {
      slNo: 2,
      status: "Dispatched",
      updatedOn: "16/10/2025 10:15 AM",
      updatedBy: "Rakesh Sharma",
      remark: "Vehicle assigned and loading in progress"
    }
  ]);

  const handleClose = () => {
    console.log("Close clicked");
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white dark:bg-gray-900 rounded-lg shadow">

          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h1 className="text-base font-medium text-gray-900 dark:text-gray-100">
              Invoice History
            </h1>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xl leading-none"
            >
              ✕
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-5 space-y-6">

            {/* Invoice Details Section */}
            <div className="space-y-4">
              <h2 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Invoice Details
              </h2>

              {/* Row 1 */}
              <div className="grid grid-cols-3 gap-6">
                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400 block mb-2">
                    Invoice No.
                  </label>
                  <Select 
                    value={formData.invoiceNo}
                    onValueChange={(value) => handleInputChange('invoiceNo', value)}
                  >
                    <SelectTrigger className="h-9 text-sm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="129403583867">129403583867</SelectItem>
                      <SelectItem value="129403583868">129403583868</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400 block mb-2">
                    Invoice Date
                  </label>
                  <Input
                    type="date"
                    value={formData.invoiceDate}
                    onChange={(e) => handleInputChange('invoiceDate', e.target.value)}
                    className="h-9 text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400 block mb-2">
                    Status
                  </label>
                  <Input
                    value={formData.status}
                    readOnly
                    className="h-9 text-sm bg-gray-50 dark:bg-gray-800"
                  />
                </div>
              </div>

              {/* Row 2 */}
              <div className="grid grid-cols-3 gap-6">
                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400 block mb-2">
                    Invoice For
                  </label>
                  <Input
                    value={formData.invoiceFor}
                    onChange={(e) => handleInputChange('invoiceFor', e.target.value)}
                    className="h-9 text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400 block mb-2">
                    Invoice Amount
                  </label>
                  <Input
                    value={formData.invoiceAmount}
                    onChange={(e) => handleInputChange('invoiceAmount', e.target.value)}
                    className="h-9 text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400 block mb-2">
                    Customer
                  </label>
                  <Input
                    value={formData.customer}
                    onChange={(e) => handleInputChange('customer', e.target.value)}
                    className="h-9 text-sm"
                  />
                </div>
              </div>

              {/* Row 3 */}
              <div className="grid grid-cols-3 gap-6">
                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400 block mb-2">
                    Destination From
                  </label>
                  <Input
                    value={formData.destinationFrom}
                    onChange={(e) => handleInputChange('destinationFrom', e.target.value)}
                    className="h-9 text-sm"
                  />
                </div>
              </div>
            </div>

            {/* Product Details Section */}
            <div className="space-y-4">
              <h2 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Product Details
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400 block mb-2">
                    Product Name
                  </label>
                  <Input
                    value={formData.productName}
                    onChange={(e) => handleInputChange('productName', e.target.value)}
                    className="h-9 text-sm"
                  />
                </div>

                <div>
                  <label className="text-xs text-gray-500 dark:text-gray-400 block mb-2">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => handleInputChange('description', e.target.value)}
                    className="w-full h-20 text-sm p-2.5 border rounded-md border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* History Section */}
            <div className="space-y-4">
              <h2 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                History
              </h2>

              <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
                {/* Table Header */}
                <div className="grid grid-cols-5 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                  <div className="px-4 py-2.5 text-xs font-medium text-gray-600 dark:text-gray-400">
                    Sl No.
                  </div>
                  <div className="px-4 py-2.5 text-xs font-medium text-gray-600 dark:text-gray-400">
                    Status
                  </div>
                  <div className="px-4 py-2.5 text-xs font-medium text-gray-600 dark:text-gray-400">
                    Status Updated on
                  </div>
                  <div className="px-4 py-2.5 text-xs font-medium text-gray-600 dark:text-gray-400">
                    Status Updated By
                  </div>
                  <div className="px-4 py-2.5 text-xs font-medium text-gray-600 dark:text-gray-400">
                    Status Updated Remark
                  </div>
                </div>

                {/* Table Body */}
                {historyData.map((item, index) => (
                  <div 
                    key={item.slNo}
                    className={`grid grid-cols-5 ${index !== historyData.length - 1 ? 'border-b border-gray-200 dark:border-gray-700' : ''}`}
                  >
                    <div className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                      {item.slNo}
                    </div>
                    <div className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                      {item.status}
                    </div>
                    <div className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                      {item.updatedOn}
                    </div>
                    <div className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                      {item.updatedBy}
                    </div>
                    <div className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                      {item.remark}
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              onClick={handleClose}
              className="h-9 px-6 text-sm bg-gray-900 hover:bg-gray-800 dark:bg-gray-700 dark:hover:bg-gray-600 text-white"
            >
              Close
            </Button>
          </div>

        </div>
      </div>
    </div>
  );
};

export default InvoiceHistory;