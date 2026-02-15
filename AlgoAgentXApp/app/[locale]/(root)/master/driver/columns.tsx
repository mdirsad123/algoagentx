"use client";

import { ColumnDef } from "@tanstack/react-table";
import { Eye, Pencil, Trash } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useTranslation } from "@/hooks/use-translations";
import { DriverBasic } from "@/types/driver-type";
import { DataTableColumnHeader } from "@/components/shared/data-table-column-header";

export const DriverColumns = ({
  onView = () => {},
  onEdit = () => {},
  onDelete = () => {},
}: {
  onView?: (data: DriverBasic) => void;
  onEdit?: (data: DriverBasic) => void;
  onDelete?: (data: DriverBasic) => void;
}): ColumnDef<DriverBasic>[] => {
  const { t, isRTL, locale } = useTranslation();

  return [
    {
      accessorKey: "driver_code",
      header: () => (
        <div className="text-gray-900 dark:text-gray-100">Driver Code</div>
      ),
      cell: ({ row }) => (
        <button
          className="text-primary hover:text-primary/60 font-semibold text-left"
          onClick={() => onView(row.original)}
        >
          {row.getValue("driver_code")}
        </button>
      ),
    },
    {
      accessorKey: "name",
      meta: "Driver Name",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Driver Name" />
      ),
    },
    {
      id: "mobileEmail",
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Contact Details" />
      ),

      cell: ({ row }) => {
        const mobile = row.original.mobile_no || "NA";
        const email = row.original.email || "NA";

        return (
          <div className="flex flex-col leading-tight">
            <span>
              <strong>Mobile No.:</strong> {mobile}
            </span>
            <span>
              <strong>Email:</strong> {email}
            </span>
          </div>
        );
      },
    },

    {
      accessorKey: "address",
      meta: "Address",
      accessorFn: (row) => {
        const parts = [
          row.param_address,
          row.country,
          row.state,
          row.city,
        ].filter(Boolean);

        return parts.join(", ");
      },
      header: ({ column }) => (
        <DataTableColumnHeader column={column} title="Address" />
      ),
    },

    {
      id: "actions",
      header: () => (
        <div className="text-gray-900 dark:text-gray-100">Actions</div>
      ),
      meta: { export: false },
      cell: ({ row }) => {
        const driver = row.original;

        const buttonClass =
          "h-9 w-9 flex items-center justify-center rounded-lg bg-white border border-gray-200 shadow-sm hover:bg-gray-100 cursor-pointer";

        return (
          <div className="flex items-center gap-3">
            {/* View */}
            <div className={buttonClass} onClick={() => onView(driver)}>
              <Eye size={18} className="text-gray-700" />
            </div>

            {/* Edit */}
            <div className={buttonClass} onClick={() => onEdit(driver)}>
              <Pencil size={18} className="text-gray-700" />
            </div>

            {/* Delete */}
            <div className={buttonClass} onClick={() => onDelete?.(driver)}>
              <Trash size={18} className="text-gray-700" />
            </div>
          </div>
        );
      },
    },
  ];
};
