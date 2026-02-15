"use client";

import { ColumnDef } from "@tanstack/react-table";
import { DataTableColumnHeader } from "@/components/shared/data-table-column-header";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Eye, MapPin, Pencil, ToggleLeft, ToggleRight, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Supplier } from "@/types/supplier-type";

export const SupplierColumns = ({
  onDelete = () => {},
  onView = () => {},
  onEdit = () => {},
  onStatusToggle = () => {},
}: {
  onDelete?: (data: Supplier) => void;
  onView?: (data: Supplier) => void;
  onEdit?: (data: Supplier) => void;
  onStatusToggle?: (data:Supplier) => void;
  
}): ColumnDef<Supplier>[] => [
  /** Supplier Code */
  {
    accessorKey: "supplier_code",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Supplier Code" />
    ),
  },

  /** Supplier Name */
  {
    accessorKey: "supplier_name",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Supplier Name" />
    ),
  },

  /** Contact Person */
  {
    accessorKey: "contact_person",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Contact Person" />
    ),
    cell: ({ row }) => row.original.contact_person || "-",
  },

  /** Address Details → One Column Layout */
  {
  id: "address_details",
  meta: "Address",
  header: ({ column }) => (
    <DataTableColumnHeader
      column={column}
      title="Address Details"
      className="dark:text-gray-200"
    />
  ),

  cell: ({ row }) => {
    const item = row.original;

    const hasAddress =
      item.address ||
      item.state ||
      item.city ||
      item.district ||
      item.country;

    const addressLine1 = item.address || "";
    const addressLine2 = [item.state, item.district, item.city]
      .filter(Boolean)
      .join(", ");

    return (
      <div className="flex items-start gap-2">

        {/* Show icon ONLY if address exists */}
        {hasAddress && (
          <MapPin className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
        )}

        <div className="text-sm text-gray-700 dark:text-gray-300 max-w-[200px]">

          {/* Line 1: Address */}
          <div>
            {addressLine1 || (hasAddress ? "" : "-")}
          </div>

          {/* Line 2: State, District, City */}
          {addressLine2 && (
            <div className="text-gray-600 dark:text-gray-400 mt-1 text-xs">
              {addressLine2}
            </div>
          )}
        </div>
      </div>
    );
  },
},

  /** Contact Details */
  {
    id: "contactDetails",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Contact Details" />
    ),
    cell: ({ row }) => {
      const item = row.original;
      return (
        <div className="text-xs leading-4 space-y-1 text-gray-700">
          <div>{item.mobile_no || "-"}</div>
          <div className="text-[11px] text-gray-500">
            {item.email || "-"}
          </div>
        </div>
      );
    },
  },

  {
  accessorKey: "status",
  header: ({ column }) => (
    <DataTableColumnHeader column={column} title="Status" />
  ),
  cell: ({ row }) => {
    const status = row.original.status;

    return (
      <span
        className={`px-2 py-1 text-xs font-bold rounded ${
          status === "Active"
            ? "bg-green-100 text-green-700"
            : "bg-red-100 text-red-700"
        }`}
      >
        {status}
      </span>
    );
  },
},

  /** Action Menu */
  {
    id: "actions",
    header: "Action",
    cell: ({ row }) => {
      const data = row.original;
      
      return (
        <div className="flex items-center space-x-2">
          <TooltipProvider>

            {/* View */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                className="p-2 rounded bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900 dark:text-green-300 dark:hover:bg-green-800"
                onClick={() => onView(data)}>
                  <Eye size={14}/>
                </Button>
              </TooltipTrigger>
              <TooltipContent>View</TooltipContent>
            </Tooltip>

            {/* Edit */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                className="p-2 rounded bg-yellow-100 text-yellow-700 hover:bg-yellow-200 dark:bg-yellow-900 dark:text-yellow-300 dark:hover:bg-yellow-800"
                onClick={() => onEdit(data)}>
                  <Pencil size={14} />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Edit</TooltipContent>
            </Tooltip>

            {/* Delete */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                className="p-2 rounded bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900 dark:text-red-300 dark:hover:bg-red-800"
                onClick={() => onDelete(data)}>
                  <Trash2 size={14} />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Delete</TooltipContent>
            </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                className="p-2 bg-blue-100 text-blue-700 hover:bg-blue-200"
                onClick={() => onStatusToggle(data)}
              >
                 {data.status === "Active" ? (
                  <ToggleRight size={16} className="text-green-600" />
                ) : (
                  <ToggleLeft size={16} className="text-red-600" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {data.status === "Active" ? "Mark Inactive" : "Mark Active"}
            </TooltipContent>
          </Tooltip>
          
          </TooltipProvider>
        </div>
      );
    },
  },


];
