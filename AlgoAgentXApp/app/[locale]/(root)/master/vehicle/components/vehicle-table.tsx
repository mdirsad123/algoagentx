"use client";

import React, { useState } from "react";
import { useDeleter, useFetcher } from "@/hooks/use-query";
import { DataTable } from "@/components/shared/data-table";
import { useRouter } from "next/navigation";
import Toast from "@/components/shared/toast";
import Swal from "sweetalert2";
import { VehicleColumns } from "../columns";
import { VehicleDetails } from "@/types/vehicle-type";
import { Button } from "@/components/ui/button";
import { RotateCcw } from "lucide-react";

type Props = { vehicleList: VehicleDetails[] };

const VehicleTable = ({ vehicleList }: Props) => {
  const router = useRouter();

  const { data } = useFetcher("/vehicle/list", "vehicleList");

  const [filters, setFilters] = useState({
    vehicle_name: "",
    vehicle_no: "",
  });

  const [filteredlist, setFilteredlist] =
    useState<VehicleDetails[]>(vehicleList);
  const [spinning, setSpinning] = useState(false);

  const applyFilter = async () => {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_SERVER}/vehicle/filterlist`,
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

  // Row View
  const handleRowView = (row: VehicleDetails) => {
    router.push(`/master/vehicle/${row.vehicle_id}`);
  };

  // Row Edit
  const handleRowEdit = (row: VehicleDetails) => {
    router.push(`/master/vehicle/edit/${row.vehicle_id}`);
  };

  const onSuccess = (response: VehicleDetails) => {
    Toast.fire({
      icon: "success",
      title: "vehicle deleted!",
    });
  };
  const onError = (error: any) => {
    console.error("Delete error:", error); // <-- logs actual backend error
    Toast.fire({
      icon: "error",
      title: "Submission Failed",
      text: error?.response?.data?.message || error.message,
    });
  };

  const deletevehicle = useDeleter(
    "vehicle/delete/",
    "vehicleList",
    onSuccess,
    onError
  );

  const handleDelete = async (row: VehicleDetails) => {
    const result = await Swal.fire({
      title: "Are you sure you want to delete this vehicle?",
      text: row.vehicle_no,
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Yes, delete",
      cancelButtonText: "Cancel",
    });

    if (result.isConfirmed) {
      deletevehicle.mutate(row.vehicle_id);
    }
  };

  return (
    <div className="w-full p-4">
      <div className="w-full bg-white p-4 rounded-lg shadow-sm border flex flex-wrap items-end gap-4">
        <div className="flex flex-col w-56">
          <label className="text-sm font-medium text-gray-700 mb-1">
            Vehicle Make
          </label>
          <input
            className="border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none p-2 rounded-md text-sm"
            placeholder="Search Vehicle Make"
            value={filters.vehicle_name}
            onChange={(e) =>
              setFilters({ ...filters, vehicle_name: e.target.value })
            }
          />
        </div>

        <div className="flex flex-col w-56">
          <label className="text-sm font-medium text-gray-700 mb-1">
            Vehicle No.
          </label>
          <input
            className="border border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none p-2 rounded-md text-sm"
            placeholder="Search Vehicle No."
            value={filters.vehicle_no}
            onChange={(e) =>
              setFilters({ ...filters, vehicle_no: e.target.value })
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
              setFilters({ vehicle_name: "", vehicle_no: "" });
              setFilteredlist(vehicleList);
            }}
          >
            <RotateCcw
              size={16}
              className={
                spinning ? "animate-spin [animation-direction:reverse]" : ""
              }
            />
          </Button>
        </div>
      </div>
      <DataTable
        columns={VehicleColumns({
          onEdit: handleRowEdit,
          onView: handleRowView,
          onDelete: handleDelete,
        })}
        data={filteredlist}
        showSearch={false}
        showPagination={true}
        paginationOptions={{ showRowCount: true, showPageSize: true }}
        exportOptions={{
          csv: true,
          pdf: true,
          filename: "vehicle",
          title: "vehicle List",
        }}
      />
    </div>
  );
};

export default VehicleTable;
