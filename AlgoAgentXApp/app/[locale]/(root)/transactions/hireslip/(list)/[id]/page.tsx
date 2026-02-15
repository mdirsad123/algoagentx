"use client";

import FormHeader from "@/components/shared/form-header";
import { Building2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import { useEffect } from "react";
import AppearingforForm from "../../components/hireslip-form";

type Props = {};
const Page = (props: Props) => {
  const param = useParams(); // Access dynamic route parameters

  const { data, isLoading } = useFetcher(
    `/master/appearingfor/${param.id}`,
    "appearingforbyid"
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

  const handleClose = () => {
    // Navigate back to the roles list
    window.location.href = "/master/appearingfor";
  };

  return (
    <>
      <FormHeader title="View Appearing for" Icon={Building2} backUrl="/master/appearingfor" />
      {/* <AppearingforForm AppearingType={data} readOnly={true} /> */}
      <div className="flex justify-end px-6 pb-6">
      </div>
    </>
  );
};

export default Page;
