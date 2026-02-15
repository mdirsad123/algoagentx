"use client";

import FormHeader from "@/components/shared/form-header";
import HireSlipForm from "../../components/hireslip-form"
import { Building2, Hand } from "lucide-react";
import { any } from "zod";

type Props = {};  
const Supplier = (props: Props) => {
  return (
    <>
    <FormHeader title="Add New Hire Slip" Icon={Building2} backUrl="/master/role" />
      <HireSlipForm onClose={() => {}} />
    </>
  );
};

export default Supplier;
