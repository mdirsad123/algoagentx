"use client";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormField,
  FormItem,
  FormControl,
  FormLabel,
  FormMessage
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import Toast from "@/components/shared/toast";
import { z } from "zod";
import Cookies from "js-cookie";
import { useRouter, useParams } from "next/navigation";
import { CategorySchema } from "@/schemas/category-schema";
import { usePoster, useUpdater } from "@/hooks/use-query";

type FormInputs = z.infer<typeof CategorySchema>;

type CategoryFormProps = {
  category?: any;
  readOnly?: boolean;
  ispopup?: boolean; 
  onSuccessInline?: (category: any) => void; 
};

const CategoryForm = ({ category, readOnly = false,onSuccessInline ,ispopup}: CategoryFormProps) => {
  const param = useParams();
  const router = useRouter();
  const isEditMode = !ispopup && !!param["id"];  // otherwise in popup it is open as edit form
  const isViewMode = readOnly;

  const [loggedinuserid] = useState(Cookies.get("loggedinuserid"));

  const form = useForm<FormInputs>({
    resolver: zodResolver(CategorySchema),
    defaultValues: category
      ? {
          category_code: category.category_code??"",
          category_name: category.category_name??"",
          category_desc: category.category_desc??""
        }
      : {
        category_code:"",
        category_name:"",
        category_desc:""
      }
  });

  /** Reset form when edit */
  useEffect(() => {
    if (category) {
      form.reset({
        category_code: category.category_code,
        category_name: category.category_name,
        category_desc: category.category_desc
      });
    }
  }, [category,form]);

  /** API Calls */
  const onSuccess = (res:any) => {
    Toast.fire({
      icon: "success",
      title: isEditMode
        ? "Category Updated Successfully!"
        : "Category Added Successfully!"
    });

     // ✅ Inline usage (popup)
  if (ispopup && onSuccessInline && res?.category) {
    onSuccessInline(res.category);
    return;
  }

    router.push("/master/category");
  };

  const onError = (e: any) => {
    Toast.fire({
      icon: "error",
      title: e?.response?.data?.message || "Something went wrong"
    });
  };

  const addCategory = usePoster(
    "/category/add",
    "categoryList",
    onSuccess,
    onError
  );

  const updateCategory = useUpdater(
    `/category/update/${param["id"]}`,
    "categorybyid",
    onSuccess,
    onError
  );


  const onSubmit = (values: FormInputs) => {


    if (!isEditMode) {
      const data = {
        ...values,
        created_by: Number(loggedinuserid),
        created_on: new Date().toISOString()
      };
      addCategory.mutate(data);
    } else {
      const data = {
        ...values,
        modified_by: Number(loggedinuserid),
        modified_on: new Date().toISOString()
      };
      updateCategory.mutate(data);
    }
  };

  const headingText = isViewMode
    ? "View Category"
    : isEditMode
    ? "Edit Category"
    : "Add Category";


     useEffect(() => {       //
        console.log(form.formState.errors);
      }, [form.formState.errors]);

  return (
    <Form {...form}>
      <div className={ispopup ? "p-4":"min-h-screen p-6"}>
        <div className=" bg-white">

          {/* {!ispopup && (
          <div className="p-6 border-b border-gray-200">
            <button
              onClick={() => router.push("/master/category")}
              className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back
            </button>

            <h1 className="text-2xl font-semibold text-gray-900">
              {headingText}
            </h1>
          </div>
          )} */}

          {/* Disable when viewing */}
          <div className={readOnly ? "pointer-events-none opacity-80" : ""}>
            
           <div className={ispopup ? "space-y-4" : "p-6 space-y-6"}>
              <div className={ispopup ? "grid grid-cols-1 gap-4" : "grid lg:grid-cols-[220px_280px_550px] md:grid-cols-2 gap-6"}>
                
                <FormField
                  control={form.control}
                  name="category_code"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        Category Code
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Category Code"
                          {...field}
                          disabled={isEditMode} 
                          readOnly={isEditMode}
                          className="h-10"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="category_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-gray-700">
                        Category Name <span className="text-red-500">*</span>
                      </FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Enter Category Name"
                          {...field}
                          disabled={isViewMode}
                          className="h-10"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              

              <FormField
                control={form.control}
                name="category_desc"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-700">
                      Category Description 
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Enter Description"
                        {...field}
                        disabled={isViewMode}
                        value={field.value??""}
                        className="h-10"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
            </div>
            </div>

              {!readOnly && (
                <div className="flex justify-end gap-4 p-4">
                  <Button
                    type="submit"
                    className="px-6 py-2 bg-gray-800 text-white rounded-md"
                    onClick={form.handleSubmit(onSubmit)}
                  >
                    {isEditMode ? "Update" : "Save"}
                  </Button>

                  <Button
                    type="button"
                    className="px-6 py-2 bg-red-600 text-white rounded-md"
                    onClick={() => {
                      if (ispopup) {
                        // 👇 opened from Supplier → close popup only
                        onSuccessInline?.(null);
                      } else {
                        // 👇 normal Category page
                        router.push("/master/category");
                      }
                    }}
                  >
                    Cancel
                  </Button>

                </div>
              )}
        {isViewMode && (
              <div className="flex justify-end gap-3 p-4">
                <Button
                  type="button"
                  className="px-6 py-2 bg-red-600 text-white rounded-md  dark:border-gray-600 dark:text-gray-200"
                  onClick={() => router.push("/master/category")}
                >
                  Close
                </Button>
              </div>
            )}
            
          </div>

        </div>
      {/* </div> */}
    </Form>
  );
};

export default CategoryForm;
