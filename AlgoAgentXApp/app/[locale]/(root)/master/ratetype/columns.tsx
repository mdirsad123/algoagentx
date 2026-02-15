"use client";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Checkbox } from "@/components/ui/checkbox";
import { Tooltip } from "@radix-ui/react-tooltip";
import { TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { ColumnDef } from "@tanstack/react-table";
import {
  MoreHorizontal,
  Pencil,
} from "lucide-react";
import { DataTableColumnHeader } from "@/components/shared/data-table-column-header";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { RateType } from "@/types/ratetype-type";

// This type is used to define the shape of our data.
// You can use a Zod schema here if you want.
  
export const RateTypeColumns=({
  onEdit = () => {},
  onDelete = () => {},
}: {
  onEdit?: (data: RateType) => void;
  onDelete?: (data: RateType) => void;
}): ColumnDef<RateType>[] => [
  
    {
    accessorKey: "rate_type",
    meta: "Rate Type | Code",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Rate Type | Code" className="w-[50%]" />
    ),
    cell: ({ row }) => (
      <div>
        <div> {row.original.rate_type} </div>
        <div>{row.original.rate_type_code} </div>
      </div>
    ),
  },
    
  {
    accessorKey: "description",
    meta: "Description",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Description"/>
    ),
  },
  
   {
  accessorKey: "created_info",
  header: ({ column }) => (
    <DataTableColumnHeader column={column} title="Created By | On" />
  ),
  cell: ({ row }) => {
    const name = row.original.fullname;
    const date = row.original.created_on
      ? new Date(row.original.created_on).toLocaleDateString()
      : "";

    return <span>{name} | {date}</span>;
  },
},

  {
    id: "actions",
    header: "Actions",
    cell: ({ row }) => {

      const ratetype = row.original;


       return (
                <div className="py-4 px-2 flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    {/* View button (always visible) */}
                   
                    {/* Edit button (conditional) */}
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          onClick={() => onEdit(ratetype)}
                          className="p-2 rounded bg-yellow-100 dark:bg-yellow-800 text-yellow-700 dark:text-yellow-200 hover:bg-yellow-200 dark:hover:bg-yellow-700 flex items-center justify-center"
                          title="Edit Order"
                        >
                          <Pencil size={16} />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>Edit</TooltipContent>
                    </Tooltip>
                  </div>
                </div>
              );

    },
  },
];

