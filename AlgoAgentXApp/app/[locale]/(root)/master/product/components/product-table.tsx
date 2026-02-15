"use client";
import { DataTable } from "@/components/shared/data-table";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAtom } from "jotai";
import { atomCompany } from "@/stores";
import { CircleCheck, CircleIcon, CircleX } from "lucide-react";
import { ThreeDots } from "react-loader-spinner";
import Confirmation from "@/components/shared/confirmation";
import { Icon } from "@/types/common-types";
import { useDeleter, useFetcher } from "@/hooks/use-query";
import Toast from "@/components/shared/toast";
import { useForm } from "react-hook-form";
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
import { Country, State, City, IState, ICity } from "country-state-city";
import DatePicker from "@/components/ui/date-picker";
import { ProductType } from "@/types/product-type";
import { ProductColumns } from "../columns";

type Props = { productlist: ProductType[] };

const ProductTable = ({ productlist }: Props) => {
  const router = useRouter();
  const onSuccess = (data: any, response: ProductType) => {
    Toast.fire({
      icon: "success",
      title: data.message,
    });
  };
  const onError = (data: any, response: ProductType) => {
    Toast.fire({
      icon: "error",
      title: data.message,
    });
  };

  const handleRowEdit = (row: ProductType) => {
    router.push(`/master/product/edit/${row.product_id}`); 
  };

  const deleteproduct = useDeleter(
    "/product/delete",
    "product-list-full",
    onSuccess,
    onError
  );

  const handleRowDelete = (row: ProductType) => {
    Confirmation({
      title: "Do you want to delete this Product?",
      icon: Icon.WARNING,
      showCancel: true,
      description: "You won't be able to revert this.",
      confirmColor: "red",
      cancelColor: "gray",
      confirmButtonText: "Yes",
    }).then((result) => {
      if (result.isConfirmed) {
        deleteproduct.mutate(Number(row.product_id)); // ✅ correct final version
      }
    });
  };

  return (
    <div className="flex flex-col">
      <section className="px-2">
        <DataTable
          columns={ProductColumns({
            onDelete: handleRowDelete,
            onEdit: handleRowEdit,
          })}
          data={productlist}
          showSearch={true}
          showPagination={true}
          paginationOptions={{ showRowCount: true, showPageSize: true }}
          exportOptions={{
            csv: true,
            pdf: true,
            filename: "product",
            title: "Product List",
          }}
        />
      </section>
    </div>
  );
};

export default ProductTable;
