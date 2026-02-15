"use client";

import FormHeader from "@/components/shared/form-header";
import InvoiceForm from "../../components/invoice-form"
import { Building2, Hand } from "lucide-react";
import { any } from "zod";

type Props = {};  
const Supplier = (props: Props) => {
  return (
    <>
    <FormHeader title="Add New Invoice Detail" Icon={Building2} backUrl="/master/role" />
      <InvoiceForm onClose={() => {}} />
    </>
  );
};

export default Supplier;
