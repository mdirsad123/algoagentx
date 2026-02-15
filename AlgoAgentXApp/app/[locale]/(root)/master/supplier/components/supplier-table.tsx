"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Swal from "sweetalert2";
import Toast from "@/components/shared/toast";
import { DataTable } from "@/components/shared/data-table";
import { useFetcher, useDeleter } from "@/hooks/use-query";
import { SupplierColumns } from "../columns";
import { Supplier } from "@/types/supplier-type";
import { Button } from "@/components/ui/button";
import { SupplierStatusDialog } from "./statuspopup";
import Cookies from "js-cookie";
import { RotateCcw } from "lucide-react";

type Props = {
  supplierList: Supplier[];
};

const SupplierTable = ({ supplierList }: Props) => {
  const router = useRouter();

  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));

  const [filters, setFilters] = useState({
      supplier_name: "",
      mobile_no: "",
      email: "",
    });
    
    const [statusDialogOpen, setStatusDialogOpen] = useState(false);
    const [selectedSupplier, setSelectedSupplier] = useState<Supplier | null>(null);
  const [spinning, setSpinning] = useState(false);

    const [filteredlist, setFilteredlist] = useState<Supplier[]>(supplierList);

     useEffect(() => {
      setSpinning(true);
    setTimeout(() => setSpinning(false), 600);
        setFilteredlist(supplierList);
      }, [supplierList]);

      const handleStatusSubmit = (newStatus: string) => {
  if (!selectedSupplier) return;

  fetch(
    `${process.env.NEXT_PUBLIC_API_SERVER}/supplier/update/${selectedSupplier.supplier_id}`,
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
        
        setFilteredlist((prev) =>
          prev.map((supplier) =>
            supplier.supplier_id === selectedSupplier.supplier_id
              ? { ...supplier, status: newStatus }
              : supplier
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
          `${process.env.NEXT_PUBLIC_API_SERVER}/supplier/filterlist`,
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

  const handleRowView = (row: Supplier) => {
    router.push(`/master/supplier/${row.supplier_id}`);
  };

  const handleRowEdit = (row: Supplier) => {
    router.push(`/master/supplier/edit/${row.supplier_id}`);
  };

  const onSuccess = () => {
    Toast.fire({
      icon: "success",
      title: "Supplier Deleted Successfully!",
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
    "supplier/delete/",
    "supplierList",
    onSuccess,
    onError
  );

  const handleDelete = async (row: Supplier) => {
    const result = await Swal.fire({
      title: "Are you sure?",
      text: row.supplier_name,
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Yes, delete",
      cancelButtonText: "Cancel",
    });

    if (result.isConfirmed) {
      deleteSupplier.mutate(row.supplier_id);
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
            value={filters.supplier_name}
            onChange={(e) =>
              setFilters({ ...filters, supplier_name: e.target.value })
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
            className="bg-orange-600 hover:bg-orange-700 text-white h-10 px-5"
          >
            Search
          </Button>
      
          <Button
            className="h-10 px-5"
            variant="outline"
            onClick={() => {
              setFilters({ supplier_name: "", mobile_no: "", email: "" });
              setFilteredlist(supplierList);
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
        columns={SupplierColumns({
          onEdit: handleRowEdit,
          onView: handleRowView,
          onDelete: handleDelete,
          onStatusToggle: (row: Supplier) => {
            setSelectedSupplier(row);
            setStatusDialogOpen(true);
          },
        })}
        data={filteredlist}
        showSearch={false}
        showPagination={true}
        paginationOptions={{ showRowCount: true, showPageSize: true }}
        exportOptions={{
          csv: true,
          pdf: true,
          filename: "supplier",
          title: "Supplier List",
        }}
      />

      <SupplierStatusDialog
              open={statusDialogOpen}
              onClose={() => setStatusDialogOpen(false)}
              supplier={selectedSupplier}
              onSubmit={handleStatusSubmit}
            />
    </div>
  );
};

export default SupplierTable;
