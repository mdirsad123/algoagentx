"use client";

import FormHeader from "@/components/shared/form-header";
import { Building2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import { useEffect } from "react";
import ProductForm from "../../components/product-form";

type Props = {};
const Page = (props: Props) => {

  const param = useParams();
  
  const { data,isLoading,refetch} = useFetcher(
    `/product/get-product-byid/${param.id}`,
    "productbyid",
    false
  );

  useEffect(()=>{
    if(param.id)
    refetch()
    console.log(data)
  },[param.id,refetch])
  
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
      <ProductForm ProductEdit={data} />
    </>
  );
};

export default Page;
