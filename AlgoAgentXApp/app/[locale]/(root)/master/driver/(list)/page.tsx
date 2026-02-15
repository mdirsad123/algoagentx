"use client";
import React, { useEffect } from 'react'
import { ThreeDots } from 'react-loader-spinner';
import { useFetcher } from '@/hooks/use-query';
import DriverTable from '../components/driver-table';
import { useRecordCount } from "../../use-record-count";

function Page() {
  const { setCount } = useRecordCount(); // Get the setCount function

  const { data, isLoading } = useFetcher(
    `/driver/driverlist`,
    "driverList"
  );

  // Update count when data changes
  useEffect(() => {
    if (data) {
      setCount('driver', data.length); // Set the driver count
    }
  }, [data, setCount]);

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
        <DriverTable driverList={data || []} />
      </div>
    </>
  );
}

export default Page;