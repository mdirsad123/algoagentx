"use client";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import React, { useEffect, useState } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { useFetcher, usePoster } from "@/hooks/use-query";
import { z } from "zod";
import Toast from "@/components/shared/toast";
import { zodResolver } from "@hookform/resolvers/zod";
import Cookies from "js-cookie";
import { useUpdater } from "@/hooks/use-query";
import { useRouter } from "next/navigation";
import { Textarea } from "@/components/ui/textarea";
import { useParams, useSearchParams } from "next/navigation";
import { ProductType } from "@/types/product-type";
import { ProductSchema } from "@/schemas/product-schema";

type ProductFormProps = {
  ProductEdit?: ProductType;
};

export default function ProductForm({
  ProductEdit,
}: ProductFormProps) {
  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));
  const param = useParams();
  const router = useRouter();

  type FormInputs = {
    product_name: string;
    product_code: string;
    description : string;
  };

  const form = useForm<FormInputs>({
    resolver: zodResolver(ProductSchema),

    defaultValues: ProductEdit
      ? {
          product_name: ProductEdit.product_name,
          product_code: ProductEdit.product_code,
          description: ProductEdit.description,
        }
      : undefined,
  });

  const onSuccess = (data: any, response: ProductType) => {
    Toast.fire({
      icon: "success",
      title: data.message,
    });
    router.push("/master/product");
  };

  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e.response?.data?.message,
    });
  };

  const saveProduct = usePoster(
    "/product/add",
    "productAdd",
    onSuccess,
    onError
  );

  const updateProduct = useUpdater(
    `/product/update/${param["id"]}`,
    "productupdate",
    onSuccess,
    onError
  );

  const onSubmit = (values: FormInputs) => {

    let payload;

    console.log("paramid", param["id"]);

    if (param["id"]) {
    
      payload = {
        ...values,
        modified_by: Number(loggedinuserid),
        modified_on: new Date(),
      };

      updateProduct.mutate(payload);

      console.log("update payload", payload);
    } else {
   
      payload = {
        ...values,
        created_by: Number(loggedinuserid),
        created_on: new Date(),
      };

      saveProduct.mutate(payload);
    }
  };


  useEffect(() => {
    console.log("❌ Form Errors:", form.formState.errors);
  }, [form.formState.errors]);

  return (
  <Form {...form}>
    <form onSubmit={form.handleSubmit(onSubmit)} className="max-w-full">

      {/* MAIN CONTAINER (needed for button positioning) */}

      <div className="relative p-6 bg-white w-full">

        {/* MAIN FIELDS */}
        <div className="grid grid-cols-2 gap-6 mb-10">

          {/* Code */}
          <FormField
            control={form.control}
            name="product_code"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Code</FormLabel>
                <FormControl>
                  <Input {...field} maxLength={20} placeholder="Enter product code" className="h-10" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Rate Type */}
          <FormField
            control={form.control}
            name="product_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>
                  Product Name <span className="text-red-500">*</span>
                </FormLabel>
                <FormControl>
                  <Input {...field} maxLength={100} placeholder="Enter product name" className="h-10" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Description (full width) */}
          <div className="col-span-1">
           <FormField
          control={form.control}
          name="description"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Description</FormLabel>
              <FormControl>
                <Textarea
                  {...field}
                  maxLength={100}
                  placeholder="Enter description"
                  className="min-h-24"
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
          </div>
        </div>

        {/* === FIXED BUTTONS AT BOTTOM-RIGHT INSIDE WHITE BOX === */}
        <div className="absolute bottom-6 right-6 flex gap-4">
          <Button type="submit" className="bg-green-700 text-white px-6">
            Save
          </Button>

          <Button
            type="button"
            className="border-red-500"
            onClick={() => router.push("/master/product")}
            variant="outline"
          >
            Cancel
          </Button>
        </div>

      </div>
    </form>
  </Form>
);
}
