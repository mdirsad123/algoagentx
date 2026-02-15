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
import { ColumnDef } from "@tanstack/react-table";
import { Tooltip } from "@radix-ui/react-tooltip";
import { TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  MoreHorizontal,
  Pencil,
} from "lucide-react";
import { DataTableColumnHeader } from "@/components/shared/data-table-column-header";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useFetcher } from "@/hooks/use-query";
import { ProductType } from "@/types/product-type";
  
export const ProductColumns=({
  onEdit = () => {},
  onDelete = () => {},
}: {
  onEdit?: (data: ProductType) => void;
  onDelete?: (data: ProductType) => void;
}): ColumnDef<ProductType>[] => [
  
    {
    accessorKey: "product_name",
    meta: "Product | Code",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Product | Code" className="w-[50%]" />
    ),
    cell: ({ row }) => (
      <div>
        <div> {row.original.product_name} </div>
        <strong>Code :</strong> <span>{row.original.product_code} </span>
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

      const product = row.original;


       return (
                <div className="py-4 px-2 flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    {/* View button (always visible) */}
                   
                    {/* Edit button (conditional) */}
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          onClick={() => onEdit(product)}
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

