"use client";

import React from "react";
import VehiclweForm from "../components/vehicle-form";
import { useParams } from "next/navigation";

function Page() {
  // ✅ Use useParams hook to get route params in client component
  const params = useParams();

  return <VehiclweForm param={params} />;
}

export default Page;

