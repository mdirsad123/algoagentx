"use client";

import { useParams } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import { useEffect } from "react";
import OrderproductForm from "../../components/orders-form";
import { FormMode } from "@/types/common-types";

const Page = () => {
  const param = useParams();

  const { data, isLoading, refetch } = useFetcher(
    `/order/orderbyid/${param.id}`,
    "orderbyid"
  );

  console.log("Response from API:", data);

useEffect(() => {     
    if (param.id) {
      refetch();
    }
  }, [param.id]);

  if (!data || !data.order) {
  return <div className="p-5 text-red-600">Order not found!</div>;
}

  return (
    <>
      {/* IMPORTANT → pass order=data */}
      <OrderproductForm 
    mode={FormMode.EDIT}
    order={data.order}
  />
    </>
  );
};

export default Page;
