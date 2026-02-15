"use client";

import { useParams } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import { useEffect } from "react";
import FleetCompanyForm from "../../components/fleetcompany-form";

type Props = {};
const Page = (props: Props) => {
  const param = useParams(); // Access dynamic route parameters

  const { data, isLoading } = useFetcher(
    `/company/${param.id}`,
    "companyview"
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
      <FleetCompanyForm company={data?.company} readOnly={true} />
      <div className="flex justify-end px-6 pb-6">
      </div>
    </>
  );
};

export default Page;
