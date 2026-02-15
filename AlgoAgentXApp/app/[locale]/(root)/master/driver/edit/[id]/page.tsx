"use client";

import { useParams } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ThreeDots } from "react-loader-spinner";
import DriverMasterParent from "../../components/driver-master-parent";

export default function Page() {
  const param = useParams();

  console.log("📌 Edit Page Loaded");
  console.log("📌 Param:", param);

  const { data, isLoading } = useFetcher(
    `/driver/driverbyid/${param.id}`,
    "driverfullbyid"
  );

  console.log("📌 API Response:", data);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <ThreeDots height="80" width="80" color="#4fa94d" />
      </div>
    );
  }

  if (!data) return <div>No driver found</div>;

  return (
    <DriverMasterParent
      mode="edit"
      id={param.id}
      personal={data.personal}
      nominees={data.nominees || []}
      documents={data.documents || []}
      bank={data.bank || []}
      info={data.info || {}}
    />
  );
}
