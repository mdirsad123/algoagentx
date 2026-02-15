"use client";

import { useParams } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import { useEffect } from "react";
import VehiclweForm from "../../components/vehicle-form";


type Props = {};
const Page = (props: Props) => {
  const param = useParams();
  
  const { data,isLoading,error} = useFetcher(
    `/vehicle/vehiclebyid/${param.id}`,
    `vehicleeditbyid-${param.id}`
  );

   useEffect(() => {
  
  }, [data, isLoading, error]); // ✅ Include all dependencies
  
  if (isLoading) {
    return (
      <div className="flex justify-center items-center">
        <section className="p-5">
          <ThreeDots
            height="80"
            width="80"
            color="#4fa94d"
            ariaLabel="tail-spin-loading"
            wrapperStyle={{}}
            wrapperClass=""
            visible={true}
          />
        </section>
      </div>
    );
  }
  return (
    <>
      {/* <VehiclweForm vehicle={data?.data || []} /> */}
       <VehiclweForm 
        vehicle={data.data} // ✅ Pass the actual data object, not array
        param={param} // ✅ Pass param for update logic
        readOnly={false} // ✅ Edit mode
      />
    </>
  );
};

export default Page;
