"use client";
import React, { useEffect } from "react";
import { ThreeDots } from "react-loader-spinner";
import { useFetcher, useDeleter } from "@/hooks/use-query";
import { Destination } from "@/types/destination-type";
import Swal from "sweetalert2";
import DestinationTable from "../components/destination-table";
import { useRecordCount } from "../../use-record-count";

function Page() {

  const { setCount } = useRecordCount();
  
  const { data, isLoading } = useFetcher(
     "/destination/destination-list",
    "destinationlist"
  );


  const deleteDestination = useDeleter(
    "/destination/delete/",
    "destinationlist",
    () => {
      Swal.fire("Deleted!", "Destination deleted successfully.", "success");
    },
    (err: any) => {
      Swal.fire(
        "Error!",
        err?.response?.data?.message || "Delete failed",
        "error"
      );
    },
  );

  const handleDelete = async (item: Destination) => {
    const res = await Swal.fire({
      title: "Are you sure?",
      text: "Do you want to delete this destination?",
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Delete",
      cancelButtonText: "Cancel",
    });

    if (res.isConfirmed) {
      deleteDestination.mutate(item.destination_id);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <ThreeDots height="80" width="80" color="#4fa94d" />
      </div>
    );
  }

  return (
    <DestinationTable
      destinationList={data?.data || []}
    />
  );
}

export default Page;