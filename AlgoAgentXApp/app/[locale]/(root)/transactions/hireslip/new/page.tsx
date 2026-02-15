"use client";

import FormHeader from "@/components/shared/form-header";
import Supplierform from "../components/hireslip-form"
import { Building2, Hand } from "lucide-react";
import { any } from "zod";
import HireSlipForm from "../components/hireslip-form";

type Props = {};  
const HireSlip = (props: Props) => {
  return (
    <>
    <FormHeader title="Add New Hire Slip" Icon={Building2} backUrl="/transactions/hireslip" />
      <HireSlipForm onClose={any}/>
    </>
  );
};

export default HireSlip;