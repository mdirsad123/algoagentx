"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Swal from "sweetalert2";
import Toast from "@/components/shared/toast";
import { DataTable } from "@/components/shared/data-table";
import { useDeleter, useUpdater } from "@/hooks/use-query";
import { CustomerColumns } from "../columns";
import { Button } from "@/components/ui/button";
import { CustomerStatusDialog } from "./statuspopup";
import Cookies from "js-cookie";
import { RotateCcw } from "lucide-react";

type Props = {
  customerList: Customer[];
};

const CustomerTable = ({ customerList }: Props) => {
  const router = useRouter();
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));
  const [spinning, setSpinning] = useState(false);

  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);

  const [filters, setFilters] = useState({
    customer_name: "",
    mobile_no: "",
    email: "",
  });
  
  const [filteredlist, setFilteredlist] = useState<Customer[]>(customerList);

  useEffect(() => {
    setSpinning(true);
    setTimeout(() => setSpinning(false), 600);
    setFilteredlist(customerList);
  }, [customerList]);

const handleStatusSubmit = (newStatus: string) => {
  if (!selectedCustomer) return;

  fetch(
    `${process.env.NEXT_PUBLIC_API_SERVER}/customer/update/${selectedCustomer.customer_id}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: newStatus,
        status_updatedby: Number(loggedinuserid),
        status_updatedon: new Date(),
      }),
    }
  )
    .then((response) => response.json())
    .then((result) => {
      if (result.success) {
        Toast.fire({
          icon: "success",
          title: "Status Updated Successfully!",
        });
        setStatusDialogOpen(false);
        
        // Trigger a re-fetch by updating the state
        setFilteredlist((prev) =>
          prev.map((customer) =>
            customer.customer_id === selectedCustomer.customer_id
              ? { ...customer, status: newStatus }
              : customer
          )
        );
      }
    })
    .catch((error) => {
      Toast.fire({
        icon: "error",
        title: "Status Update Failed",
        text: error?.message || "Something went wrong",
      });
    });
};

  const applyFilter = async () => {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_SERVER}/customer/filterlist`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(filters),
        }
      );
  
      const result = await res.json();
      setFilteredlist(result);
    } catch (error) {
      console.error("Filter Error:", error);
    }
  };

  const handleRowView = (row: Customer) => {
    router.push(`/master/customer/${row.customer_id}`);
  };

  const handleRowEdit = (row: Customer) => {
    router.push(`/master/customer/edit/${row.customer_id}`);
  };

  const onSuccess = () => {
    Toast.fire({
      icon: "success",
      title: "Customer Deleted Successfully!",
    });
  };

  const onError = (error: any) => {
    console.error("Delete error:", error);
    Toast.fire({
      icon: "error",
      title: error?.response?.data?.message || "Delete Failed",
    });
  };

  const deleteSupplier = useDeleter(
    "Customer/delete/",
    "customerList",
    onSuccess,
    onError
  );

  const handleDelete = async (row: Customer) => {
    const result = await Swal.fire({
      title: "Are you sure?",
      text: row.customer_name,
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Yes, delete",
      cancelButtonText: "Cancel",
    });

    if (result.isConfirmed) {
      deleteSupplier.mutate(row.customer_id);
    }
  };

  return (
    <div className="w-full p-4">
      <div className="w-full bg-white p-4 rounded-lg shadow-sm border flex flex-wrap items-end gap-4">
        <div className="flex flex-col w-56">
          <label className="text-sm font-medium text-gray-700 mb-1">
            Customer Name
          </label>
          <input
            className="border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none p-2 rounded-md text-sm"
            placeholder="Search Customer Name"
            value={filters.customer_name}
            onChange={(e) =>
              setFilters({ ...filters, customer_name: e.target.value })
            }
          />
        </div>

        <div className="flex flex-col w-56">
          <label className="text-sm font-medium text-gray-700 mb-1">
            Mobile No.
          </label>
          <input
            className="border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none p-2 rounded-md text-sm"
            placeholder="Search Mobile No."
            value={filters.mobile_no}
            onChange={(e) =>
              setFilters({ ...filters, mobile_no: e.target.value })
            }
          />
        </div>

        <div className="flex flex-col w-56">
          <label className="text-sm font-medium text-gray-700 mb-1">
            Email
          </label>
          <input
            className="border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none p-2 rounded-md text-sm"
            placeholder="Search Email"
            value={filters.email}
            onChange={(e) =>
              setFilters({ ...filters, email: e.target.value })
            }
          />
        </div>

        <div className="flex items-center gap-2 mt-1">
          <Button
            onClick={applyFilter}
            className="bg-orange-500 hover:bg-orange-600 text-white h-10 px-5"
          >
            Search
          </Button>

          <Button
            className="h-10 px-5"
            variant="outline"
            onClick={() => {
              setFilters({ customer_name: "", mobile_no: "", email: "" });
              setFilteredlist(customerList);
            }}
          >
             <RotateCcw
                size={16}
                className={
                  spinning
                    ? "animate-spin [animation-direction:reverse]"
                    : ""
                }
              />
          </Button>
        </div>
      </div>

      <DataTable
        columns={CustomerColumns({
          onEdit: handleRowEdit,
          onView: handleRowView,
          onDelete: handleDelete,
          onStatusToggle: (row: Customer) => {
            setSelectedCustomer(row);
            setStatusDialogOpen(true);
          },
        })}
        data={filteredlist}
        showPagination={true}
        paginationOptions={{ showRowCount: true, showPageSize: true }}
        exportOptions={{
          csv: true,
          pdf: true,
          filename: "Customer",
          title: "Customer List",
        }}
      />

      <CustomerStatusDialog
        open={statusDialogOpen}
        onClose={() => setStatusDialogOpen(false)}
        customer={selectedCustomer}
        onSubmit={handleStatusSubmit}
      />
    </div>
  );
};

export default CustomerTable;