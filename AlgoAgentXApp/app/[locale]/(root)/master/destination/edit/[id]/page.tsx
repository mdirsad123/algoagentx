"use client";

import FormHeader from "@/components/shared/form-header";
import { Building2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import { useEffect } from "react";
import DestinationForm from "../../components/destination-form";

type Props = {};
const Page = (props: Props) => {
  const param = useParams();
  
  const { data, isLoading, refetch, isSuccess } = useFetcher(
    `/destination/destinationbyid/${param.id}`, // Changed to match view page
    "destinationbyidforedit"
  );

  useEffect(() => {
    console.log("Edit data:", data);
  }, [data]); // Changed dependency to data
  
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
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
      <DestinationForm destination={data} mode="edit" /> {/* Added mode prop */}
    </>
  );
};

export default Page;