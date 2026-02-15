"use client";

import React from "react";
import { useRouter } from "next/navigation";
import Swal from "sweetalert2";
import Toast from "@/components/shared/toast";
import { DataTable } from "@/components/shared/data-table";
import { useFetcher, useDeleter } from "@/hooks/use-query";
import { CategoryColumns } from "../columns";
import { Category } from "@/types/category-type";

type Props = {categoryList : Category[]};

const CategoryTable = ({categoryList}:Props) => {
  const router = useRouter();

  /** Fetch Category List */
  const { data } = useFetcher("/category/list", "categoryList");

  /** View Action */
  const handleRowView = (row: Category) => {
    router.push(`/master/category/${row.category_id}`);
  };

  /** Edit Action */
  const handleRowEdit = (row: Category) => {
    router.push(`/master/category/edit/${row.category_id}`);
  };

  /** Delete API Call */
  const onSuccess = () => {
    Toast.fire({
      icon: "success",
      title: "Category Deleted Successfully!"
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
    "category/delete/",
    "categoryList",
    onSuccess,
    onError
  );

  /** Delete confirmation */
  const handleDelete = async (row: Category) => {
    const result = await Swal.fire({
      title: "Are you sure?",
      text: row.category_name,
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Yes, delete",
      cancelButtonText: "Cancel",
    });

    if (result.isConfirmed) {
      deleteCategory.mutate(row.category_id);
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
        data={categoryList}
        showSearch={true}
        showPagination={true}
        paginationOptions={{ showRowCount: true, showPageSize: true }}
        exportOptions={{
          csv: true,
          pdf: true,
          filename: "category",
          title: "Category List",
        }}
      />
    </div>
  );
};

export default CategoryTable;
