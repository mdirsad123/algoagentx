"use client";

import { useParams } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import { useEffect } from "react";
import FleetCompanyForm from "../../components/fleetcompany-form";


type Props = {};
const Page = (props: Props) => {
  const param = useParams();
  
  const { data,isLoading,refetch} = useFetcher(
    `/company/${param.id}`,
    "companyedited"
  );

  console.log("got data on edit",data)

  useEffect(()=>{
    refetch()
  },[])
  
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
      <FleetCompanyForm company={data?.company} />
    </>
  );
};

export default Page;
