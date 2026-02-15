"use client";

import {
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormControl,
} from "@/components/ui/form";
import { Eye } from "lucide-react";

type DocumentProps = {
  form: any;
  existingFiles?: {
    invoice_document?: string | null;
    rc_document?: string | null;
    insurance_document?: string | null;
  };
  readOnly?: boolean; // true = view mode
  isEditMode?: boolean; // true only when editing
};

const VehicleDocumentsForm = ({
  form,
  existingFiles = {},
  readOnly = false,
  isEditMode = false,
}: DocumentProps) => {
  return (
    <div className="space-y-6">
      <h2 className="font-semibold text-lg text-gray-800 border-b pb-2">
        Documents Upload
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* --------------------------------------------------------
           REUSABLE DOCUMENT FIELD COMPONENT
        -------------------------------------------------------- */}
        <DocUploadField
          label="Invoice Document"
          fieldName="invoice_document"
          form={form}
          existingFile={existingFiles.invoice_document}
          readOnly={readOnly}
        />

        <DocUploadField
          label="RC Document"
          fieldName="rc_document"
          form={form}
          existingFile={existingFiles.rc_document}
          readOnly={readOnly}
        />

        <DocUploadField
          label="Insurance Document"
          fieldName="insurance_document"
          form={form}
          existingFile={existingFiles.insurance_document}
          readOnly={readOnly}
        />
      </div>
    </div>
  );
};

/* --------------------------------------------------------
   COMPONENT: Individual Upload Field
-------------------------------------------------------- */

const DocUploadField = ({
  label,
  form,
  fieldName,
  existingFile,
  readOnly,
}: {
  label: string;
  form: any;
  fieldName: string;
  existingFile?: string | null;
  readOnly?: boolean;
}) => {
  return (
    <FormField
      control={form.control}
      name={fieldName}
      render={({ field: { value, onChange, ...rest } }) => {
        const selectedFile = value?.[0];

        return (
          <FormItem>
            <FormLabel className="text-gray-800 pl-3">{label}</FormLabel>

            <div className="flex items-center gap-3 pl-3">
              {!readOnly && (
                <>
                  <FormControl>
                    <input
                      {...rest}
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png"
                      onChange={(e) => onChange(e.target.files)}
                      id={fieldName}
                      className="hidden"
                    />
                  </FormControl>

                  <label
                    htmlFor={fieldName}
                    className="cursor-pointer px-3 py-2 bg-gray-200 hover:bg-gray-300 rounded-md shadow-sm text-sm"
                  >
                    Upload File
                  </label>
                </>
              )}

              {existingFile && (
                <a
                  href={`http://localhost:4000/uploads/${existingFile}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800"
                >
                  <Eye size={22} />
                </a>
              )}
            </div>

            {!selectedFile && existingFile && (
              <p className="text-xs text-gray-600 mt-1 italic pl-3">
                Existing: {existingFile}
              </p>
            )}

            {selectedFile && !readOnly && (
              <p className="text-xs text-green-700 mt-1 font-semibold pl-3">
                Selected: {selectedFile.name}
              </p>
            )}

            <FormMessage />
          </FormItem>
        );
      }}
    />
  );
};

export default VehicleDocumentsForm;
