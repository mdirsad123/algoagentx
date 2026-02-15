"use client";

import React from "react";
import { useRouter } from "next/navigation";
import Swal from "sweetalert2";
import Toast from "@/components/shared/toast";
import { DataTable } from "@/components/shared/data-table";
import { useFetcher, useDeleter } from "@/hooks/use-query";
import { CategoryColumns } from "../columns";
import { Vehiclemake } from "@/types/vehiclemake-type";

type Props = {vehiclemakeList : Vehiclemake[]};

const VehiclemakeTable = ({vehiclemakeList}:Props) => {
  const router = useRouter();

  const { data } = useFetcher("/vehiclemake/list", "vehiclemakeList");

  const handleRowView = (row: Vehiclemake) => {
    router.push(`/master/vehiclemake/${row.make_id}`);
  };

  const handleRowEdit = (row: Vehiclemake) => {
    router.push(`/master/vehiclemake/edit/${row.make_id}`);
  };

  const onSuccess = () => {
    Toast.fire({
      icon: "success",
      title: "Vehiclemake Deleted Successfully!"
    });
  };

  const onError = (error: any) => {
    console.error("Delete error:", error);
    Toast.fire({
      icon: "error",
      title: error?.response?.data?.message || "Delete Failed"
    });
  };

  const deleteCategory = useDeleter(
    "vehiclemake/delete/",
    "categoryList",
    onSuccess,
    onError
  );

  const handleDelete = async (row: Vehiclemake) => {
    const result = await Swal.fire({
      title: "Are you sure?",
      text: row.vehicle_name,
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Yes, delete",
      cancelButtonText: "Cancel",
    });

    if (result.isConfirmed) {
      deleteCategory.mutate(row.make_id);
    }
  };

  return (
    <div className="w-full p-4">
      <DataTable
        columns={CategoryColumns({
          onEdit: handleRowEdit,
          onView: handleRowView,
          onDelete: handleDelete,
        })}
        data={vehiclemakeList}
        showSearch={true}
        showPagination={true}
        paginationOptions={{ showRowCount: true, showPageSize: true }}
        exportOptions={{
          csv: true,
          pdf: true,
          filename: "vehiclemake",
          title: "Vehiclemake List",
        }}
      />
    </div>
  );
};

export default VehiclemakeTable;
