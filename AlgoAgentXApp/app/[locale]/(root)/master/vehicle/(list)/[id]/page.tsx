"use client";

import { useParams } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import { useEffect } from "react";
import VehiclweForm from "../../components/vehicle-form";

type Props = {};
const Page = (props: Props) => {
  const param = useParams(); // Access dynamic route parameters

  const { data, isLoading } = useFetcher(
    `/vehicle/vehiclebyid/${param.id}`,
    "vehicleview"
  );

  useEffect(() => {
    console.log(data);
  }, [data]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center">
        <section className="p-5">
          <ThreeDots
            height="80"
            width="80"
            color="#4fa94d"
            ariaLabel="loading-indicator"
          />
        </section>
      </div>
    );
  }

  return (
    <>
      <VehiclweForm vehicle={data.data}   param={param} readOnly={true} />
    </>
  );
};

export default Page;
