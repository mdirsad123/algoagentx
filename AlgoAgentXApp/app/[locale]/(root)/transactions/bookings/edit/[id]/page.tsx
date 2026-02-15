"use client";

import FormHeader from "@/components/shared/form-header";
import { FileText } from "lucide-react";
import { useParams } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import { useEffect } from "react";
import BookingForm from "../../components/booking-form";

type Props = {};

const Page = (props: Props) => {
  const param = useParams();

  const { data, isLoading } = useFetcher(
    `/transaction/booking/${param.id}`,
    `booking-${param.id}`
  );

  useEffect(() => {
    console.log("📦 Booking Data:", data);
  }, [data]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
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
     <BookingForm booking={data?.booking} mode="edit" />
    </>
  );
};

export default Page;