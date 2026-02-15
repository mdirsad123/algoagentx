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
import {  useForm } from "react-hook-form";
import { Form,FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Country, State, City, IState, ICity } from "country-state-city";
import DatePicker from "@/components/ui/date-picker";
import { RateType } from "@/types/ratetype-type";
import { RateTypeColumns } from "../columns";

type Props = {rattypelist : RateType[]};

const RateTypeTable = ({rattypelist}: Props) => {
const router = useRouter();
  const onSuccess = (data :any, response: RateType) => {
    Toast.fire({
      icon: "success",
      title:  data.message,
    });
    
  };
  const onError = (data :any, response: RateType) => {
    Toast.fire({
      icon: "error",
      title: data.message,
    });
  };

   const handleRowEdit = (row: RateType) => {
      router.push(`/master/ratetype/edit/${row.rate_type_id}`); // Add ?from=company
      }

const deleteratetype = useDeleter('/ratetype/deleteratetype', "ratetype-list-full", onSuccess, onError);

const handleRowDelete = (row: RateType) => {
  Confirmation({
    title: "Do you want to delete this rate type?",
    icon: Icon.WARNING,
    showCancel: true,
    description: "You won't be able to revert this.",
    confirmColor: "red",
    cancelColor: "gray",
    confirmButtonText: "Yes",
  }).then((result) => {
    if (result.isConfirmed) {
      deleteratetype.mutate(Number(row.rate_type_id)); // ✅ correct final version
    }
  });
};


  const { data: stafftypeList } = useFetcher(
      `employee/employeetype`,
      "employeetype"
    );

    return (
      <div className="flex flex-col">
        <section className="px-2">
          <DataTable
            columns={RateTypeColumns({ onDelete:handleRowDelete , onEdit:handleRowEdit })}
            data={rattypelist}
            showSearch={true}
            showPagination={true}
            paginationOptions={{ showRowCount: true, showPageSize: true }}
            exportOptions={{ csv: true, pdf: true, filename: "ratetype", title: "Rate Type List" }}
          />
        </section>
      </div>
    );
    
};

export default RateTypeTable;
