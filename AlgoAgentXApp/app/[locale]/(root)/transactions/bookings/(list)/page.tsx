"use client";
import React, { useEffect } from "react";
import { ThreeDots } from "react-loader-spinner";
import { useFetcher } from "@/hooks/use-query";
import { useRecordCount } from "../../use-record-count";
import BookingTable from "../components/booking-table";

function Page() {
  const { setCount } = useRecordCount(); // Get the setCount function

  const { data, isLoading } = useFetcher(
    `/transaction/booking/bookinglist`,
    "bookingList"
  );

const bookingList = data?.data ?? [];

useEffect(() => {
  setCount("booking", bookingList.length);
}, [bookingList.length, setCount]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center">
        <section className="p-5">
          <ThreeDots height="80" width="80" color="#4fa94d" />
        </section>
      </div>
    );
  }

  return (
    <>
      <div className="p-5">
        <BookingTable bookinglist={bookingList} />
      </div>
    </>
  );
}

export default Page;
