"use client";

import { useParams } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import { useEffect } from "react";
import VehiclemakeForm from "../../components/vehiclemake-form";


type Props = {};
const Page = (props: Props) => {
  const param = useParams();
  
  const { data,isLoading} = useFetcher(
    `/vehiclemake/${param.id}`,
    "vehiclemakedit"
  );

  useEffect(()=>{
    console.log(data)
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
      <VehiclemakeForm vehiclemake={data} />
    </>
  );
};

export default Page;
