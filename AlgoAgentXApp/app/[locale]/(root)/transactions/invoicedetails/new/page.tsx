"use client";

import FormHeader from "@/components/shared/form-header";
import Supplierform from "../components/invoice-form"
import { Building2, Hand } from "lucide-react";
import { any } from "zod";

type Props = {};  
const Supplier = (props: Props) => {
  return (
    <>
    <FormHeader title="Add New Supplier" Icon={Building2} backUrl="/master/role" />
      <Supplierform onClose={any}/>
    </>
  );
};

export default Supplier;
